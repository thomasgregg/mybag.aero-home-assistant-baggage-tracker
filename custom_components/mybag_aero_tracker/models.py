"""Data models for MyBag Tracker."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass
class BaggageStatus:
    """Structured status returned by the tracker client."""

    state: str
    checked_at: datetime
    airline: str
    reference_number: str
    family_name: str
    url: str
    message: str
    is_searching: bool
    bag_title: str | None = None
    headline: str | None = None
    details: str | None = None
    tracing_statuses: list[str] | None = None
    primary_tracing_status: str | None = None
    status_steps: list[str] | None = None
    current_status_text: str | None = None
    status_body: str | None = None
    delivery_details: dict | None = None
    no_of_bags_updated: int | None = None
    record_status: str | None = None
    raw_excerpt: str | None = None
