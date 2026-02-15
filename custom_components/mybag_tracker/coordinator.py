"""Coordinator for MyBag Tracker updates."""

from __future__ import annotations

from datetime import timedelta
import logging

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .api import MyBagApiClient
from .models import BaggageStatus

_LOGGER = logging.getLogger(__name__)


class MyBagDataUpdateCoordinator(DataUpdateCoordinator[BaggageStatus]):
    """Data update coordinator for MyBag Tracker."""

    def __init__(self, hass: HomeAssistant, client: MyBagApiClient, interval_minutes: int) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name="MyBag Tracker",
            update_interval=timedelta(minutes=interval_minutes),
        )
        self.client = client

    async def _async_update_data(self) -> BaggageStatus:
        return await self.client.async_check_status()
