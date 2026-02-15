"""Constants for the MyBag Tracker integration."""

from __future__ import annotations

from datetime import timedelta

DOMAIN = "mybag_aero_tracker"

CONF_AIRLINE = "airline"
CONF_REFERENCE_NUMBER = "reference_number"
CONF_FAMILY_NAME = "family_name"
CONF_SCAN_INTERVAL_MINUTES = "scan_interval_minutes"

DEFAULT_SCAN_INTERVAL_MINUTES = 60
DEFAULT_TIMEOUT_SECONDS = 90

SEARCHING_TEXT = "SEARCHING FOR YOUR BAGGAGE"
NO_RECORD_TEXT = "NO RECORD WAS FOUND"

API_BASE_URL = "https://wtss-api.mybag.aero"
MANAGE_LOGIN_ENDPOINT = "/manageLogin"
API_KEY = "P"

AIRLINE_URLS = {
    "austrian": "https://mybag.aero/baggage/#/pax/austrian/en-gb/delayed/manage-bag",
    "lufthansa": "https://mybag.aero/baggage/#/pax/lufthansa/en-gb/delayed/manage-bag",
    "swiss": "https://mybag.aero/baggage/#/pax/swiss/en-gb/delayed/manage-bag",
}

AIRLINE_CODES = {
    "austrian": "OS",
    "lufthansa": "LH",
    "swiss": "LX",
}

UPDATE_INTERVAL = timedelta(minutes=DEFAULT_SCAN_INTERVAL_MINUTES)

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
)
