"""Koordinátory Recuair – lokálna jednotka a voliteľný cloud."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import timedelta
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .cloud import RecuairCloud, RecuairCloudError
from .const import CLOUD_SCAN_INTERVAL, DOMAIN
from .local import RecuairError, RecuairLocal, RecuairState

_LOGGER = logging.getLogger(__name__)


class RecuairCoordinator(DataUpdateCoordinator[RecuairState]):
    """Pravidelne číta stav jednotky z lokálnej siete."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, api: RecuairLocal, scan_interval: int) -> None:
        super().__init__(
            hass, _LOGGER, config_entry=entry, name=f"{DOMAIN}_local", update_interval=timedelta(seconds=scan_interval)
        )
        self.api = api

    async def _async_update_data(self) -> RecuairState:
        try:
            state = await self.api.fetch()
        except RecuairError as err:
            raise UpdateFailed(str(err)) from err
        state.last_update = dt_util.utcnow()
        return state

    async def async_command(self, coro: Any, **optimistic: Any) -> None:
        """Pošle príkaz, hneď zobrazí očakávaný stav a potom načíta skutočný."""
        try:
            await coro
        except RecuairError as err:
            raise HomeAssistantError(str(err)) from err
        if self.data is not None and optimistic:
            self.async_set_updated_data(replace(self.data, **optimistic))
        await self.async_request_refresh()


class RecuairCloudCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Voliteľné hodnoty z cloudu Recuair."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, cloud: RecuairCloud, device_id: int) -> None:
        super().__init__(hass, _LOGGER, config_entry=entry, name=f"{DOMAIN}_cloud", update_interval=CLOUD_SCAN_INTERVAL)
        self.cloud = cloud
        self.device_id = device_id

    async def _async_update_data(self) -> dict[str, Any]:
        try:
            return await self.cloud.observation(self.device_id, dt_util.now().date())
        except RecuairCloudError as err:
            raise UpdateFailed(str(err)) from err


@dataclass
class RecuairRuntime:
    """Objekty integrácie uložené v konfiguračnom zázname."""

    local: RecuairCoordinator
    cloud: RecuairCloudCoordinator | None = None
