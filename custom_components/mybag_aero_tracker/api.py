"""HTTP API checker for mybag.aero."""

from __future__ import annotations

import base64
import json
import re
from datetime import UTC, datetime

from aiohttp import ClientSession

from . import const as integration_const
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
        self._bag_status_catalog: dict[str, dict] | None = None
        self._notification_catalog: dict[str, dict] | None = None

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
            response_status = 0
            response_text = ""
            for validator in (1, 0):
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
                        "Validator": validator,
                        "LoginAfterTimeInDays": 21,
                        "captchaResponse": "",
                    }
                }

                async with self._session.post(
                    f"{API_BASE_URL}{MANAGE_LOGIN_ENDPOINT}",
                    json=payload,
                    headers=headers,
                ) as response:
                    response_text = await response.text()
                    response_status = response.status

                # 200 is success.
                if response_status == 200:
                    break
                # 401 is a hard "not found", no need to retry.
                if response_status == 401:
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
                # 489/490/492 can happen based on validator behavior; try the fallback validator.
                if response_status not in (489, 490, 492):
                    break

            if response_status != 200:
                return self._error_status(
                    f"mybag API returned HTTP {response_status}: {response_text[:300]}"
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
            primary_tracing_status = tracing_statuses[0] if tracing_statuses else None
            status_steps, current_status_text, status_body = await self._resolve_status_messages(
                primary_tracing_status
            )

            no_of_bags_updated = delayed_bags.get("noOfBagsUpdated", 0)
            if not isinstance(no_of_bags_updated, int):
                try:
                    no_of_bags_updated = int(no_of_bags_updated)
                except (TypeError, ValueError):
                    no_of_bags_updated = 0

            is_searching = self._is_searching_state(no_of_bags_updated, tracing_statuses)

            first_bag = bag_items[0] if bag_items else {}
            bag_title = self._build_bag_title(first_bag)
            delivery_details = self._extract_delivery_details(delayed_record)

            headline = (
                SEARCHING_TEXT
                if is_searching
                else current_status_text or "BAGGAGE STATUS UPDATED"
            )
            details = (
                "Please check back later"
                if is_searching
                else status_body or "Status changed from SEARCHING FOR YOUR BAGGAGE"
            )
            message = (
                "Still searching for your baggage."
                if is_searching
                else status_body or "Good news: baggage status changed."
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
                primary_tracing_status=primary_tracing_status,
                status_steps=status_steps,
                current_status_text=current_status_text,
                status_body=status_body,
                delivery_details=delivery_details,
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

    async def _load_status_catalog(self) -> None:
        if self._bag_status_catalog is not None and self._notification_catalog is not None:
            return
        self._bag_status_catalog = {}
        self._notification_catalog = {}
        try:
            async with self._session.get(DYNAMIC_MESSAGES_URL, headers={"User-Agent": USER_AGENT}) as response:
                if response.status != 200:
                    return
                payload = json.loads(await response.text())
            dynamic = payload.get("dynamicMessages", {})
            bag_status = dynamic.get("bag_status", {})
            notification = dynamic.get("notification_mszs", {})
            if isinstance(bag_status, dict):
                self._bag_status_catalog = bag_status
            if isinstance(notification, dict):
                self._notification_catalog = notification
        except Exception:
            # Keep integration resilient if static message lookup fails.
            self._bag_status_catalog = {}
            self._notification_catalog = {}

    async def _resolve_status_messages(self, tracing_status: str | None) -> tuple[list[str] | None, str | None, str | None]:
        if not tracing_status:
            return None, None, None
        await self._load_status_catalog()

        status_entry = (self._bag_status_catalog or {}).get(tracing_status)
        if not isinstance(status_entry, dict):
            return None, None, None

        open_heads: list[tuple[int, str]] = []
        for key, value in status_entry.items():
            if not (key.startswith("BTS_ACCopen_") and key.endswith("_head")):
                continue
            if not isinstance(value, str) or not value.strip():
                continue
            match = re.search(r"BTS_ACCopen_(\d+)_head", key)
            order = int(match.group(1)) if match else 999
            open_heads.append((order, value.strip()))

        open_heads.sort(key=lambda item: item[0])
        steps: list[str] = []
        for _, value in open_heads:
            if value not in steps:
                steps.append(value)

        current_status_text = status_entry.get("BTS_ACCclose_head")
        if isinstance(current_status_text, str):
            current_status_text = current_status_text.strip() or None
        else:
            current_status_text = None
        if not current_status_text and steps:
            current_status_text = steps[-1]

        status_body = (
            ((self._notification_catalog or {}).get(tracing_status, {})).get("delayed", {}).get("body")
        )
        if isinstance(status_body, str):
            status_body = status_body.strip() or None
        else:
            status_body = None

        return (steps or None), current_status_text, status_body

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

    def _extract_delivery_details(self, delayed_record: dict) -> dict | None:
        details: dict[str, str] = {}

        delayed_group = delayed_record.get("DelayedBagGroup", {})
        delayed_bags = delayed_group.get("DelayedBags", {})
        bag_items = delayed_bags.get("DelayedBag", []) or []
        first_bag = bag_items[0] if bag_items else {}

        # Structured bag delivery timestamps
        bag_delivery = first_bag.get("BagDelivery", {})
        status = bag_delivery.get("Status", {})
        pickup = ((status.get("TrackingUpdate") or {}).get("value") or "").strip()
        scheduled = ((status.get("OutForDelivery") or {}).get("value") or "").strip()
        if pickup:
            details["pickup_datetime_local"] = pickup
        if scheduled:
            details["scheduled_delivery_local"] = scheduled

        # Passenger/contact details
        passenger = delayed_record.get("Passengers", {})
        contact = passenger.get("ContactInfo", {})
        permanent = contact.get("PermanentAddress", {})
        last_name = (((passenger.get("Names") or {}).get("Name") or [{}])[0].get("value") or "").strip()
        if last_name:
            details["passenger_name"] = last_name
        phone = ((((contact.get("CellPhones") or {}).get("Phone")) or [{}])[0].get("value") or "").strip()
        if phone:
            details["telephone_number"] = phone

        addr_line = (((permanent.get("AddressLine") or [{}])[0].get("value")) or "").strip()
        city = ((permanent.get("City") or {}).get("value") or "").strip()
        state = ((permanent.get("State") or {}).get("value") or "").strip()
        postal = ((permanent.get("PostalCode") or {}).get("value") or "").strip()
        country_obj = permanent.get("Country") or {}
        country = (country_obj.get("value") or "").strip()
        country_code = (country_obj.get("Code") or "").strip().upper()
        if not country and country_code:
            country = {"DE": "Germany", "AT": "Austria", "CH": "Switzerland"}.get(country_code, country_code)
        address_parts = [x for x in [addr_line, city, state, postal, country] if x]
        if address_parts:
            details["delivery_address"] = ", ".join(address_parts)

        # Bag details
        tag = first_bag.get("BagTag", {})
        airline_tag = (tag.get("AirlineCode") or "").strip()
        tag_seq = (tag.get("TagSequence") or "").strip()
        if airline_tag and tag_seq:
            details["tag_details"] = f"{airline_tag}{tag_seq}"
        color_code = (((first_bag.get("ColorTypeDesc") or {}).get("ColorCode")) or "").strip().upper()
        if color_code:
            details["baggage_colour"] = {
                "GY": "Grey",
                "BL": "Blue",
                "BK": "Black",
                "RD": "Red",
                "WH": "White",
            }.get(color_code, color_code)

        if bag_items:
            details["number_of_baggage_in_delivery"] = str(len(bag_items))

        # Encoded delivery details block (source for courier website and commission date)
        delivery_info_text = ""
        ai = delayed_record.get("AdditionalInfo", {})
        delivery_info = ai.get("DeliveryInfo", {}) if isinstance(ai, dict) else {}
        if isinstance(delivery_info, dict):
            text_list = delivery_info.get("Text", [])
            if isinstance(text_list, list) and text_list:
                first_text = text_list[0]
                if isinstance(first_text, dict):
                    delivery_info_text = (first_text.get("value") or "").strip()

        if delivery_info_text:
            for line in [ln.strip() for ln in delivery_info_text.splitlines()]:
                if line.startswith("DS "):
                    parts = [p.strip() for p in line[3:].split(" - ") if p.strip()]
                    if len(parts) >= 2:
                        details["delivery_reference"] = parts[0]
                        details["delivery_service"] = parts[1]
                elif line.startswith("CW "):
                    raw = line[3:].strip()
                    site = raw.replace("/D/", ".").strip("/")
                    if site:
                        details["courier_website"] = site
                        details["courier_tracking_url"] = (
                            site if site.lower().startswith(("http://", "https://")) else f"https://{site}"
                        )
                elif line.startswith("ZP "):
                    # Example: ZP 14476 .DD 18FEB .DW ...
                    match = re.search(r"\.DD\s+([A-Z0-9]+)", line)
                    if match:
                        details["commission_date"] = match.group(1).strip()
                elif line.startswith("CT01 ") and "baggage_type" not in details:
                    details["baggage_type"] = line[5:].strip()

        # Email fallback for human-readable baggage type and note text.
        email_info = delayed_record.get("EmailInfo", {})
        text_items = email_info.get("Text", []) if isinstance(email_info, dict) else []
        candidate = None
        if isinstance(text_items, list):
            for item in reversed(text_items):
                if not isinstance(item, dict):
                    continue
                value = item.get("value")
                if isinstance(value, str) and "Baggage Delivery Order Created" in value:
                    candidate = value
                    break

        if candidate:
            marker = "ADVICE TO CUSTOMER - PLEASE NOTE"
            if marker in candidate and "note" not in details:
                details["note"] = candidate.split(marker, 1)[1].strip()

            if "baggage_type" not in details:
                bag_type_match = re.search(
                    r"Bag\s*-\s*\d+\s*Type\s*\d+\s*:\s*(.+)",
                    candidate,
                    re.IGNORECASE,
                )
                if bag_type_match:
                    details["baggage_type"] = bag_type_match.group(1).strip()

            created_match = re.search(
                r"Baggage Delivery Order Created by\s+([^\n]+)",
                candidate,
                re.IGNORECASE,
            )
            if created_match:
                details["created_by"] = created_match.group(1).strip()

        cleaned = {k: v for k, v in details.items() if v}
        return cleaned or None

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
AIRLINE_CODES = integration_const.AIRLINE_CODES
API_BASE_URL = integration_const.API_BASE_URL
API_KEY = integration_const.API_KEY
MANAGE_LOGIN_ENDPOINT = integration_const.MANAGE_LOGIN_ENDPOINT
SEARCHING_TEXT = integration_const.SEARCHING_TEXT
USER_AGENT = integration_const.USER_AGENT
# Backward-safe fallback in case HA has a stale const.py during update.
DYNAMIC_MESSAGES_URL = getattr(
    integration_const,
    "DYNAMIC_MESSAGES_URL",
    "https://mybag.aero/baggage/assets/static/common-dynamic-messages/en-gb.json",
)
