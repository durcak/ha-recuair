"""Senzory Recuair."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import (
    PERCENTAGE,
    REVOLUTIONS_PER_MINUTE,
    EntityCategory,
    UnitOfEnergy,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import RecuairConfigEntry
from .const import MODES
from .entity import RecuairEntity
from .local import RecuairState

try:  # HA 2026.x
    from homeassistant.const import UnitOfRatio

    CONCENTRATION_PARTS_PER_MILLION = UnitOfRatio.PARTS_PER_MILLION
except ImportError:  # staršie verzie
    from homeassistant.const import CONCENTRATION_PARTS_PER_MILLION


@dataclass(frozen=True, kw_only=True)
class LocalSensorDescription(SensorEntityDescription):
    """Senzor z lokálnej jednotky."""

    value_fn: Callable[[RecuairState], Any]


@dataclass(frozen=True, kw_only=True)
class CloudSensorDescription(SensorEntityDescription):
    """Senzor z cloudu Recuair."""

    value_fn: Callable[[dict[str, Any]], Any]
    attrs_fn: Callable[[dict[str, Any]], dict[str, Any]] | None = None


def _float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


LOCAL_SENSORS: tuple[LocalSensorDescription, ...] = (
    LocalSensorDescription(
        key="co2", translation_key="co2", device_class=SensorDeviceClass.CO2,
        native_unit_of_measurement=CONCENTRATION_PARTS_PER_MILLION, state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda s: s.co2,
    ),
    LocalSensorDescription(
        key="room_temperature", translation_key="room_temperature", device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS, state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda s: s.room_temperature,
    ),
    LocalSensorDescription(
        key="outside_temperature", translation_key="outside_temperature", device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS, state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda s: s.outside_temperature,
    ),
    LocalSensorDescription(
        key="humidity", translation_key="humidity", device_class=SensorDeviceClass.HUMIDITY,
        native_unit_of_measurement=PERCENTAGE, state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda s: s.humidity,
    ),
    LocalSensorDescription(
        key="ventilation_intensity", translation_key="ventilation_intensity", native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT, value_fn=lambda s: s.ventilation,
    ),
    LocalSensorDescription(
        key="filter_status", translation_key="filter_status", native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT, value_fn=lambda s: s.filter_used,
    ),
    LocalSensorDescription(
        key="mode", translation_key="mode", device_class=SensorDeviceClass.ENUM, options=MODES,
        value_fn=lambda s: s.mode if s.mode in MODES else None,
    ),
    LocalSensorDescription(
        key="light_intensity", translation_key="light_intensity", state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda s: s.light_intensity,
    ),
    LocalSensorDescription(
        key="firmware_version", translation_key="firmware_version", entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda s: s.firmware,
    ),
    LocalSensorDescription(
        key="last_successful_update", translation_key="last_successful_update",
        device_class=SensorDeviceClass.TIMESTAMP, entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda s: s.last_update,
    ),
)

CLOUD_SENSORS: tuple[CloudSensorDescription, ...] = (
    CloudSensorDescription(
        key="fan_speed_1", translation_key="fan_speed_1", native_unit_of_measurement=REVOLUTIONS_PER_MINUTE,
        state_class=SensorStateClass.MEASUREMENT, value_fn=lambda d: _float(d.get("intensityVent")),
    ),
    CloudSensorDescription(
        key="fan_speed_2", translation_key="fan_speed_2", native_unit_of_measurement=REVOLUTIONS_PER_MINUTE,
        state_class=SensorStateClass.MEASUREMENT, value_fn=lambda d: _float(d.get("fan2Rpm")),
    ),
    CloudSensorDescription(
        key="outside_humidity", translation_key="outside_humidity", device_class=SensorDeviceClass.HUMIDITY,
        native_unit_of_measurement=PERCENTAGE, state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: _float(d.get("s1ToutRh")),
    ),
    CloudSensorDescription(
        key="recovered_energy", translation_key="recovered_energy", device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR, state_class=SensorStateClass.TOTAL_INCREASING,
        suggested_display_precision=1,
        value_fn=lambda d: round(v / 3600, 3) if (v := _float(d.get("energyKj"))) is not None else None,
    ),
    CloudSensorDescription(
        key="filter_state", translation_key="filter_state", entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda d: d.get("filterState"),
    ),
    CloudSensorDescription(
        key="error_state", translation_key="error_state", entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda d: d.get("errorState"),
        attrs_fn=lambda d: {"errors": d.get("listErrors") or None, "connected": d.get("connected")},
    ),
)


async def async_setup_entry(
    hass: HomeAssistant, entry: RecuairConfigEntry, async_add_entities: AddConfigEntryEntitiesCallback
) -> None:
    """Pridá senzory."""
    runtime = entry.runtime_data
    entities: list[SensorEntity] = [RecuairLocalSensor(runtime.local, d) for d in LOCAL_SENSORS]
    if runtime.cloud is not None:
        entities += [RecuairCloudSensor(runtime.cloud, d) for d in CLOUD_SENSORS]
    async_add_entities(entities)


class RecuairLocalSensor(RecuairEntity, SensorEntity):
    """Senzor z lokálnej jednotky."""

    entity_description: LocalSensorDescription

    def __init__(self, coordinator, description: LocalSensorDescription) -> None:
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def native_value(self) -> Any:
        return self.entity_description.value_fn(self.coordinator.data) if self.coordinator.data else None


class RecuairCloudSensor(RecuairEntity, SensorEntity):
    """Senzor z cloudu Recuair."""

    entity_description: CloudSensorDescription

    def __init__(self, coordinator, description: CloudSensorDescription) -> None:
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def native_value(self) -> Any:
        return self.entity_description.value_fn(self.coordinator.data) if self.coordinator.data else None

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        if not self.entity_description.attrs_fn or not self.coordinator.data:
            return None
        return self.entity_description.attrs_fn(self.coordinator.data)
