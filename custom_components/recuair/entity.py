"""Spoločná entita Recuair."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity, DataUpdateCoordinator

from .const import DOMAIN


class RecuairEntity(CoordinatorEntity[DataUpdateCoordinator]):
    """Entita priradená k jednotke Recuair."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: DataUpdateCoordinator, key: str) -> None:
        super().__init__(coordinator)
        entry = coordinator.config_entry
        self._attr_unique_id = f"{entry.unique_id}_{key}"
        local = entry.runtime_data.local
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.unique_id)},
            name=entry.title,
            manufacturer="Recuair",
            model="DC40",
            sw_version=local.data.firmware if local.data else None,
            configuration_url=local.api.url,
        )
