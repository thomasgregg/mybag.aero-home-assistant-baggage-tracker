"""Config flow for MyBag Tracker."""

from __future__ import annotations

import re
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult

from .const import (
    AIRLINE_URLS,
    CONF_AIRLINE,
    CONF_FAMILY_NAME,
    CONF_REFERENCE_NUMBER,
    CONF_SCAN_INTERVAL_MINUTES,
    DEFAULT_SCAN_INTERVAL_MINUTES,
    DOMAIN,
)


class MyBagTrackerConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for MyBag Tracker."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            normalized_reference = re.sub(r"\s+", "", user_input[CONF_REFERENCE_NUMBER].upper())
            normalized_family_name = user_input[CONF_FAMILY_NAME].strip().upper()
            if not re.fullmatch(r"[A-Z]{3}[A-Z0-9]{2}[A-Z0-9]+", normalized_reference):
                errors[CONF_REFERENCE_NUMBER] = "invalid_reference"
            elif not normalized_family_name:
                errors[CONF_FAMILY_NAME] = "invalid_family_name"
            else:
                await self.async_set_unique_id(f"{user_input[CONF_AIRLINE]}_{normalized_reference}")
                self._abort_if_unique_id_configured()

                return self.async_create_entry(
                    title=f"{user_input[CONF_AIRLINE].title()} {normalized_reference}",
                    data={
                        CONF_AIRLINE: user_input[CONF_AIRLINE],
                        CONF_REFERENCE_NUMBER: normalized_reference,
                        CONF_FAMILY_NAME: normalized_family_name,
                        CONF_SCAN_INTERVAL_MINUTES: user_input[CONF_SCAN_INTERVAL_MINUTES],
                    },
                )

        schema = vol.Schema(
            {
                vol.Required(CONF_AIRLINE, default="austrian"): vol.In(list(AIRLINE_URLS.keys())),
                vol.Required(CONF_REFERENCE_NUMBER): str,
                vol.Required(CONF_FAMILY_NAME): str,
                vol.Required(CONF_SCAN_INTERVAL_MINUTES, default=DEFAULT_SCAN_INTERVAL_MINUTES): vol.All(
                    vol.Coerce(int), vol.Range(min=5, max=720)
                ),
            }
        )

        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: config_entries.ConfigEntry) -> config_entries.OptionsFlow:
        """Get options flow for this handler."""
        return MyBagTrackerOptionsFlow(config_entry)


class MyBagTrackerOptionsFlow(config_entries.OptionsFlow):
    """MyBag Tracker options flow."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        super().__init__()
        # Keep our own reference for broad HA-version compatibility.
        self._config_entry = config_entry

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Manage options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        current_interval = self._config_entry.options.get(
            CONF_SCAN_INTERVAL_MINUTES,
            self._config_entry.data.get(CONF_SCAN_INTERVAL_MINUTES, DEFAULT_SCAN_INTERVAL_MINUTES),
        )

        schema = vol.Schema(
            {
                vol.Required(CONF_SCAN_INTERVAL_MINUTES, default=current_interval): vol.All(
                    vol.Coerce(int), vol.Range(min=5, max=720)
                ),
            }
        )

        return self.async_show_form(step_id="init", data_schema=schema)
