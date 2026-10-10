"""Ovládanie vetrania Recuair ako ventilátor (rýchlosť 1–4, predvoľby Auto/Holiday/Bypass)."""

from __future__ import annotations

import math
from typing import Any

from homeassistant.components.fan import FanEntity, FanEntityFeature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import RecuairConfigEntry
from .const import PRESET_MODES, SPEED_MODES
from .entity import RecuairEntity


async def async_setup_entry(
    hass: HomeAssistant, entry: RecuairConfigEntry, async_add_entities: AddConfigEntryEntitiesCallback
) -> None:
    """Pridá ventilátor."""
    async_add_entities([RecuairFan(entry.runtime_data.local)])


class RecuairFan(RecuairEntity, FanEntity):
    """Vetranie jednotky."""

    _attr_translation_key = "ventilation"
    _attr_name = None
    _attr_supported_features = (
        FanEntityFeature.SET_SPEED | FanEntityFeature.PRESET_MODE | FanEntityFeature.TURN_ON | FanEntityFeature.TURN_OFF
    )
    _attr_speed_count = len(SPEED_MODES)
    _attr_preset_modes = PRESET_MODES

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator, "fan")

    @property
    def _mode(self) -> str | None:
        return self.coordinator.data.mode if self.coordinator.data else None

    @property
    def is_on(self) -> bool | None:
        return None if self._mode is None else self._mode != "off"

    @property
    def percentage(self) -> int | None:
        mode = self._mode
        if mode in SPEED_MODES:
            return int(mode) * 100 // len(SPEED_MODES)
        if mode == "off":
            return 0
        return self.coordinator.data.ventilation if self.coordinator.data else None

    @property
    def preset_mode(self) -> str | None:
        return self._mode if self._mode in PRESET_MODES else None

    async def _set_mode(self, mode: str) -> None:
        await self.coordinator.async_command(self.coordinator.api.set_mode(mode), mode=mode)

    async def async_set_percentage(self, percentage: int) -> None:
        if percentage == 0:
            await self._set_mode("off")
            return
        speed = min(len(SPEED_MODES), max(1, math.ceil(percentage * len(SPEED_MODES) / 100)))
        await self._set_mode(str(speed))

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        await self._set_mode(preset_mode)

    async def async_turn_on(
        self, percentage: int | None = None, preset_mode: str | None = None, **kwargs: Any
    ) -> None:
        if preset_mode:
            await self.async_set_preset_mode(preset_mode)
        elif percentage is not None:
            await self.async_set_percentage(percentage)
        else:
            await self._set_mode("auto")

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self._set_mode("off")
