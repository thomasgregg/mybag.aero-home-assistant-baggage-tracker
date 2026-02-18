"""Binary sensor platform for MyBag Tracker."""

from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import MyBagDataUpdateCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up MyBag Tracker binary sensor from config entry."""
    coordinator: MyBagDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([MyBagFoundBinarySensor(coordinator, entry)])


class MyBagFoundBinarySensor(CoordinatorEntity[MyBagDataUpdateCoordinator], BinarySensorEntity):
    """True when baggage no longer appears as searching."""

    _attr_has_entity_name = True
    _attr_name = "Found"
    _attr_icon = "mdi:bag-checked"

    def __init__(self, coordinator: MyBagDataUpdateCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_found"
        self._attr_translation_key = "found"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
        }

    @property
    def is_on(self) -> bool:
        """Return whether baggage is considered found."""
        data = self.coordinator.data
        return data.state not in {"searching", "not_found", "error"} and not data.is_searching
