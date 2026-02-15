"""HTTP API checker for mybag.aero."""

from __future__ import annotations

import base64
import json
import re
from datetime import UTC, datetime

from aiohttp import ClientSession

from .const import (
    AIRLINE_CODES,
    API_BASE_URL,
    API_KEY,
    MANAGE_LOGIN_ENDPOINT,
    SEARCHING_TEXT,
    USER_AGENT,
)
from .models import BaggageStatus


class MyBagApiClient:
    """Checks baggage status from mybag backend APIs."""

    def __init__(
        self,
        session: ClientSession,
        airline: str,
        reference_number: str,
        family_name: str,
        url: str,
    ) -> None:
        self._session = session
        self._airline = airline
        self._reference_number = reference_number.strip().upper()
        self._family_name = family_name.strip().upper()
        self._url = url

    async def async_check_status(self) -> BaggageStatus:
        """Check baggage status via HTTP APIs."""
        try:
            station_code, airline_code, short_reference = self._parse_file_reference(self._reference_number)
            expected_airline = AIRLINE_CODES[self._airline]
            if airline_code != expected_airline:
                return self._error_status(
                    f"Reference '{self._reference_number}' is for airline code {airline_code}, "
                    f"but selected airline expects {expected_airline}."
                )

            payload = {
                "WTR_ReadRecordRQ": {
                    "RecordID": {
                        "RecordType": "DELAYED",
                        "RecordReference": {
                            "ReferenceNumber": short_reference,
                            "StationCode": station_code,
                            "AirlineCode": airline_code,
                            "LastName": self._family_name,
                        },
                    },
                    "AgentID": "GUEST",
                    "Version": 0.1,
                    "Validator": 0,
                    "LoginAfterTimeInDays": 21,
                    "captchaResponse": "",
                }
            }

            auth_payload = {
                "fileRef": self._reference_number,
                "lastName": self._family_name,
                "epic": "DELAYED",
                "airline": airline_code,
            }
            auth_encoded = base64.b64encode(json.dumps(auth_payload, separators=(",", ":")).encode()).decode()

            headers = {
                "Accept": "application/json, text/plain, */*",
                "Content-Type": "application/json",
                "X-Api-Key": API_KEY,
                "Authorization": f"{airline_code} {auth_encoded}",
                "User-Agent": USER_AGENT,
            }

            async with self._session.post(
                f"{API_BASE_URL}{MANAGE_LOGIN_ENDPOINT}",
                json=payload,
                headers=headers,
            ) as response:
                response_text = await response.text()

            if response.status == 401:
                return BaggageStatus(
                    state="not_found",
                    checked_at=datetime.now(UTC),
                    airline=self._airline,
                    reference_number=self._reference_number,
                    family_name=self._family_name,
                    url=self._url,
                    message="No record found for reference number and family name.",
                    is_searching=False,
                )

            if response.status != 200:
                return self._error_status(
                    f"mybag API returned HTTP {response.status}: {response_text[:300]}"
                )

            response_json = json.loads(response_text)
            delayed_record = response_json.get("WTR_ReadRecordRS", {}).get("WTR_DelayedBagRecReadRS")
            if not isinstance(delayed_record, dict):
                msg = response_json.get("Msg") or response_json.get("message") or "Unexpected API response format."
                return self._error_status(msg)

            delayed_group = delayed_record.get("DelayedBagGroup", {})
            delayed_bags = delayed_group.get("DelayedBags", {})
            bag_items = delayed_bags.get("DelayedBag", []) or []

            tracing_statuses: list[str] = []
            for item in bag_items:
                status = item.get("tracingStatus")
                if isinstance(status, str) and status.strip():
                    tracing_statuses.append(status.strip())

            no_of_bags_updated = delayed_bags.get("noOfBagsUpdated", 0)
            if not isinstance(no_of_bags_updated, int):
                try:
                    no_of_bags_updated = int(no_of_bags_updated)
                except (TypeError, ValueError):
                    no_of_bags_updated = 0

            is_searching = self._is_searching_state(no_of_bags_updated, tracing_statuses)

            first_bag = bag_items[0] if bag_items else {}
            bag_title = self._build_bag_title(first_bag)

            headline = SEARCHING_TEXT if is_searching else "BAGGAGE STATUS UPDATED"
            details = (
                "Please check back later"
                if is_searching
                else "Status changed from SEARCHING FOR YOUR BAGGAGE"
            )
            message = (
                "Still searching for your baggage."
                if is_searching
                else "Good news: baggage status changed."
            )

            return BaggageStatus(
                state="searching" if is_searching else "updated",
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
                tracing_statuses=tracing_statuses,
                no_of_bags_updated=no_of_bags_updated,
                record_status=delayed_record.get("RecordStatus"),
                raw_excerpt=response_text[:1000],
            )
        except Exception as err:
            return self._error_status(f"Check failed: {err}")

    def _is_searching_state(self, no_of_bags_updated: int, tracing_statuses: list[str]) -> bool:
        if no_of_bags_updated > 0:
            return False
        if not tracing_statuses:
            return True
        return all(status.startswith("BTS_1") for status in tracing_statuses)

    def _build_bag_title(self, bag_item: dict) -> str | None:
        seq = bag_item.get("Seq")
        tag_sequence = bag_item.get("BagTag", {}).get("TagSequence")
        if tag_sequence is None:
            return None

        tag_text = str(tag_sequence).strip()
        if tag_text.isdigit():
            tag_text = tag_text.zfill(10)

        if seq is None:
            return f"DELAYED BAGGAGE - {tag_text}"
        return f"DELAYED BAGGAGE {seq} - {tag_text}"

    def _parse_file_reference(self, reference: str) -> tuple[str, str, str]:
        compact = re.sub(r"\s+", "", reference.upper())
        match = re.fullmatch(r"([A-Z]{3})([A-Z0-9]{2})([A-Z0-9]+)", compact)
        if not match:
            raise ValueError(
                "Reference must be in file-reference format, e.g. ABCOS12345 (station+airline+number)."
            )
        return match.group(1), match.group(2), match.group(3)

    def _error_status(self, message: str) -> BaggageStatus:
        return BaggageStatus(
            state="error",
            checked_at=datetime.now(UTC),
            airline=self._airline,
            reference_number=self._reference_number,
            family_name=self._family_name,
            url=self._url,
            message=message,
            is_searching=False,
        )
