"""Website checker for mybag.aero."""

from __future__ import annotations

import asyncio
import re
from datetime import datetime, UTC

from playwright.async_api import TimeoutError as PlaywrightTimeoutError
from playwright.async_api import async_playwright

from .const import NO_RECORD_TEXT, SEARCHING_TEXT, USER_AGENT
from .models import BaggageStatus


class MyBagApiClient:
    """Scrapes the baggage status from the mybag website."""

    def __init__(self, airline: str, reference_number: str, family_name: str, url: str) -> None:
        self._airline = airline
        self._reference_number = reference_number
        self._family_name = family_name
        self._url = url

    async def async_check_status(self) -> BaggageStatus:
        """Check baggage status via browser automation."""
        try:
            return await asyncio.wait_for(self._async_check_status_impl(), timeout=120)
        except Exception as err:
            return BaggageStatus(
                state="error",
                checked_at=datetime.now(UTC),
                airline=self._airline,
                reference_number=self._reference_number,
                family_name=self._family_name,
                url=self._url,
                message=f"Check failed: {err}",
                is_searching=False,
            )

    async def _async_check_status_impl(self) -> BaggageStatus:
        async with async_playwright() as pw:
            browser = await pw.chromium.launch(headless=True, args=["--no-sandbox"])
            context = await browser.new_context(user_agent=USER_AGENT)
            page = await context.new_page()

            try:
                await page.goto(self._url, wait_until="domcontentloaded", timeout=90000)
                await page.locator("#mngRptRefNoLTxt, #mngRptLastNameTxt").first.wait_for(timeout=30000)

                await self._dismiss_cookie_overlay(page)
                await page.locator("#mngRptRefNoLTxt").fill(self._reference_number)
                await page.locator("#mngRptLastNameTxt").fill(self._family_name)

                await self._dismiss_cookie_overlay(page)
                await page.locator("#mngRptLoginBtn").click()
                await page.wait_for_load_state("networkidle", timeout=30000)

                body_text = (await page.locator("body").inner_text()).upper()
                if NO_RECORD_TEXT in body_text:
                    return BaggageStatus(
                        state="not_found",
                        checked_at=datetime.now(UTC),
                        airline=self._airline,
                        reference_number=self._reference_number,
                        family_name=self._family_name,
                        url=self._url,
                        message="No record found for reference number and family name.",
                        is_searching=False,
                        raw_excerpt=self._truncate_text(body_text),
                    )

                await page.get_by_text(re.compile(r"baggage details", re.IGNORECASE)).first.click(timeout=20000)
                await page.wait_for_load_state("networkidle", timeout=30000)

                bag_body = await page.locator("body").inner_text()
                bag_body_upper = bag_body.upper()
                is_searching = SEARCHING_TEXT in bag_body_upper

                bag_title = self._extract_first_match(bag_body, r"DELAYED BAGGAGE[^\n]*")
                headline = self._extract_first_match(
                    bag_body, r"SEARCHING FOR YOUR BAGGAGE|FOUND[^\n]*|DELIVERED[^\n]*|LOCATED[^\n]*"
                )

                details = None
                if headline:
                    details = self._line_after(bag_body, headline)

                state = "searching" if is_searching else "updated"
                message = (
                    "Still searching for your baggage."
                    if is_searching
                    else "Baggage status changed from 'SEARCHING FOR YOUR BAGGAGE'."
                )

                return BaggageStatus(
                    state=state,
                    checked_at=datetime.now(UTC),
                    airline=self._airline,
                    reference_number=self._reference_number,
                    family_name=self._family_name,
                    url=self._url,
                    message=message,
                    is_searching=is_searching,
                    bag_title=bag_title,
                    headline=headline,
                    details=details,
                    raw_excerpt=self._truncate_text(bag_body_upper),
                )
            except PlaywrightTimeoutError:
                return BaggageStatus(
                    state="error",
                    checked_at=datetime.now(UTC),
                    airline=self._airline,
                    reference_number=self._reference_number,
                    family_name=self._family_name,
                    url=self._url,
                    message="Timed out while loading or navigating the baggage page.",
                    is_searching=False,
                )
            finally:
                await context.close()
                await browser.close()

    async def _dismiss_cookie_overlay(self, page) -> None:
        selectors = [
            "#onetrust-accept-btn-handler",
            "#accept-recommended-btn-handler",
            "#close-pc-btn-handler",
            ".onetrust-close-btn-handler",
        ]
        for selector in selectors:
            element = page.locator(selector).first
            if await element.count() > 0:
                try:
                    await element.click(timeout=1500)
                except Exception:
                    pass

        await page.evaluate(
            """
            () => {
              const overlay = document.querySelector('.onetrust-pc-dark-filter');
              if (overlay) overlay.remove();
              const modal = document.querySelector('#onetrust-pc-sdk');
              if (modal) modal.remove();
            }
            """
        )

    def _extract_first_match(self, text: str, pattern: str) -> str | None:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        return match.group(0).strip() if match else None

    def _line_after(self, text: str, current_line: str) -> str | None:
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        for idx, line in enumerate(lines):
            if line.lower() == current_line.lower() and idx + 1 < len(lines):
                return lines[idx + 1]
        return None

    def _truncate_text(self, text: str) -> str:
        return text[:1000]
