"""Sensor platform for MyBag Tracker."""

from __future__ import annotations

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_AIRLINE, CONF_REFERENCE_NUMBER, DOMAIN
from .coordinator import MyBagDataUpdateCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up MyBag Tracker sensor from config entry."""
    coordinator: MyBagDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([MyBagStatusSensor(coordinator, entry)])


class MyBagStatusSensor(CoordinatorEntity[MyBagDataUpdateCoordinator], SensorEntity):
    """Represents the delayed baggage status."""

    _attr_has_entity_name = True
    _attr_name = "Status"
    _attr_icon = "mdi:bag-checked"

    def __init__(self, coordinator: MyBagDataUpdateCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._entry = entry
        reference = self._entry.data[CONF_REFERENCE_NUMBER]
        self._attr_unique_id = f"{entry.entry_id}_status"
        self._attr_translation_key = "status"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": f"MyBag {reference}",
            "manufacturer": "mybag.aero",
            "model": "Delayed Baggage Tracker",
        }

    @property
    def native_value(self) -> str:
        """Return sensor state."""
        return self.coordinator.data.state

    @property
    def extra_state_attributes(self) -> dict:
        """Return structured status data."""
        data = self.coordinator.data
        return {
            "airline": data.airline,
            "reference_number": data.reference_number,
            "family_name": data.family_name,
            "bag_title": data.bag_title,
            "headline": data.headline,
            "details": data.details,
            "tracing_statuses": data.tracing_statuses,
            "primary_tracing_status": data.primary_tracing_status,
            "status_steps": data.status_steps,
            "current_status_text": data.current_status_text,
            "status_body": data.status_body,
            "no_of_bags_updated": data.no_of_bags_updated,
            "record_status": data.record_status,
            "message": data.message,
            "is_searching": data.is_searching,
            "checked_at": data.checked_at.isoformat(),
            "source_url": data.url,
            "raw_excerpt": data.raw_excerpt,
        }
