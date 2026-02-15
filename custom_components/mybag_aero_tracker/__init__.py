"""The MyBag Tracker integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import MyBagApiClient
from .const import AIRLINE_URLS, CONF_AIRLINE, CONF_FAMILY_NAME, CONF_REFERENCE_NUMBER, CONF_SCAN_INTERVAL_MINUTES, DOMAIN
from .coordinator import MyBagDataUpdateCoordinator

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.BINARY_SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up MyBag Tracker from a config entry."""
    airline = entry.options.get(CONF_AIRLINE, entry.data[CONF_AIRLINE])
    reference_number = entry.options.get(CONF_REFERENCE_NUMBER, entry.data[CONF_REFERENCE_NUMBER])
    family_name = entry.options.get(CONF_FAMILY_NAME, entry.data[CONF_FAMILY_NAME])
    interval_minutes = entry.options.get(CONF_SCAN_INTERVAL_MINUTES, entry.data[CONF_SCAN_INTERVAL_MINUTES])
    session = async_get_clientsession(hass)

    client = MyBagApiClient(
        session=session,
        airline=airline,
        reference_number=reference_number,
        family_name=family_name,
        url=AIRLINE_URLS[airline],
    )

    coordinator = MyBagDataUpdateCoordinator(hass, client, interval_minutes)
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    entry.async_on_unload(entry.add_update_listener(async_update_options))
    return True


async def async_update_options(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry when options change."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok
