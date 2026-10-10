"""Výber režimu Recuair."""

from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import RecuairConfigEntry
from .const import MODES
from .entity import RecuairEntity


async def async_setup_entry(
    hass: HomeAssistant, entry: RecuairConfigEntry, async_add_entities: AddConfigEntryEntitiesCallback
) -> None:
    """Pridá výber režimu."""
    async_add_entities([RecuairModeSelect(entry.runtime_data.local)])


class RecuairModeSelect(RecuairEntity, SelectEntity):
    """Režim jednotky: Auto, 1–4, Holiday, Bypass, Vypnuté."""

    _attr_translation_key = "mode_select"
    _attr_options = MODES

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator, "mode_select")

    @property
    def current_option(self) -> str | None:
        mode = self.coordinator.data.mode if self.coordinator.data else None
        return mode if mode in MODES else None

    async def async_select_option(self, option: str) -> None:
        await self.coordinator.async_command(self.coordinator.api.set_mode(option), mode=option)
