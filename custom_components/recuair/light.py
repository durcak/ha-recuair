"""Náladové osvetlenie Recuair (farba RGB, intenzita 0–5)."""

from __future__ import annotations

from typing import Any

from homeassistant.components.light import ATTR_BRIGHTNESS, ATTR_RGB_COLOR, ColorMode, LightEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import RecuairConfigEntry
from .const import LIGHT_MAX_INTENSITY
from .entity import RecuairEntity

DEFAULT_RGB = (255, 255, 255)


async def async_setup_entry(
    hass: HomeAssistant, entry: RecuairConfigEntry, async_add_entities: AddConfigEntryEntitiesCallback
) -> None:
    """Pridá svetlo."""
    async_add_entities([RecuairLight(entry.runtime_data.local)])


class RecuairLight(RecuairEntity, LightEntity):
    """Náladové osvetlenie jednotky."""

    _attr_translation_key = "mood_light"
    _attr_color_mode = ColorMode.RGB
    _attr_supported_color_modes = {ColorMode.RGB}

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator, "light")

    @property
    def _intensity(self) -> int | None:
        return self.coordinator.data.light_intensity if self.coordinator.data else None

    @property
    def is_on(self) -> bool | None:
        return None if self._intensity is None else self._intensity > 0

    @property
    def brightness(self) -> int | None:
        if not self._intensity:
            return None
        return round(self._intensity * 255 / LIGHT_MAX_INTENSITY)

    @property
    def rgb_color(self) -> tuple[int, int, int] | None:
        return (self.coordinator.data.light_rgb if self.coordinator.data else None) or DEFAULT_RGB

    async def async_turn_on(self, **kwargs: Any) -> None:
        rgb = tuple(kwargs.get(ATTR_RGB_COLOR) or self.rgb_color)
        if ATTR_BRIGHTNESS in kwargs:
            intensity = max(1, round(kwargs[ATTR_BRIGHTNESS] * LIGHT_MAX_INTENSITY / 255))
        else:
            intensity = self._intensity or LIGHT_MAX_INTENSITY
        await self.coordinator.async_command(
            self.coordinator.api.set_light(rgb, intensity), light_intensity=intensity, light_rgb=rgb
        )

    async def async_turn_off(self, **kwargs: Any) -> None:
        rgb = self.rgb_color
        await self.coordinator.async_command(self.coordinator.api.set_light(rgb, 0), light_intensity=0)
