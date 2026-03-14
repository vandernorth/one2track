import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    PERCENTAGE,
    UnitOfLength,
    UnitOfSpeed,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .client import TrackerDevice
from .common import DOMAIN
from .coordinator import GpsCoordinator

LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, kw_only=True)
class One2TrackSensorDescription(SensorEntityDescription):
    """Describes a One2Track sensor."""
    value_fn: Callable[[TrackerDevice], Any]


def _get_battery(device: TrackerDevice) -> int | None:
    return device.get("last_location", {}).get("battery_percentage")


def _get_balance(device: TrackerDevice) -> float | None:
    cents = device.get("simcard", {}).get("balance_cents")
    if cents is not None:
        return round(cents / 100, 2)
    return None


def _get_last_location_update(device: TrackerDevice) -> datetime | None:
    val = device.get("last_location", {}).get("last_location_update")
    if val:
        return datetime.fromisoformat(val)
    return None


def _get_last_communication(device: TrackerDevice) -> datetime | None:
    val = device.get("last_location", {}).get("last_communication")
    if val:
        return datetime.fromisoformat(val)
    return None


def _get_signal_strength(device: TrackerDevice) -> int | None:
    return device.get("last_location", {}).get("signal_strength")


def _get_satellite_count(device: TrackerDevice) -> int | None:
    return device.get("last_location", {}).get("satellite_count")


def _get_speed(device: TrackerDevice) -> float | None:
    val = device.get("last_location", {}).get("speed")
    if val is not None:
        return float(val)
    return None


def _get_altitude(device: TrackerDevice) -> float | None:
    val = device.get("last_location", {}).get("altitude")
    if val is not None:
        return float(val)
    return None


def _get_steps(device: TrackerDevice) -> int | None:
    meta = device.get("last_location", {}).get("meta_data")
    if meta:
        val = meta.get("steps")
        if val is not None:
            return int(val)
    return None


def _get_accuracy(device: TrackerDevice) -> float | None:
    meta = device.get("last_location", {}).get("meta_data")
    if meta:
        return meta.get("accuracy_meters")
    return None


def _get_status(device: TrackerDevice) -> str | None:
    val = device.get("status")
    if val is not None:
        return val.lower()
    return None


SENSOR_DESCRIPTIONS: list[One2TrackSensorDescription] = [
    One2TrackSensorDescription(
        key="battery",
        translation_key="battery",
        native_unit_of_measurement=PERCENTAGE,
        device_class=SensorDeviceClass.BATTERY,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_get_battery,
    ),
    One2TrackSensorDescription(
        key="sim_balance",
        translation_key="sim_balance",
        native_unit_of_measurement="EUR",
        device_class=SensorDeviceClass.MONETARY,
        state_class=SensorStateClass.TOTAL,
        icon="mdi:sim",
        value_fn=_get_balance,
    ),
    One2TrackSensorDescription(
        key="last_location_update",
        translation_key="last_location_update",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=_get_last_location_update,
    ),
    One2TrackSensorDescription(
        key="last_communication",
        translation_key="last_communication",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=_get_last_communication,
    ),
    One2TrackSensorDescription(
        key="signal_strength",
        translation_key="signal_strength",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:signal",
        value_fn=_get_signal_strength,
    ),
    One2TrackSensorDescription(
        key="satellite_count",
        translation_key="satellite_count",
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:satellite-variant",
        value_fn=_get_satellite_count,
    ),
    One2TrackSensorDescription(
        key="speed",
        translation_key="speed",
        native_unit_of_measurement=UnitOfSpeed.KILOMETERS_PER_HOUR,
        device_class=SensorDeviceClass.SPEED,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_get_speed,
    ),
    One2TrackSensorDescription(
        key="altitude",
        translation_key="altitude",
        native_unit_of_measurement=UnitOfLength.METERS,
        device_class=SensorDeviceClass.DISTANCE,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:altimeter",
        value_fn=_get_altitude,
    ),
    One2TrackSensorDescription(
        key="steps",
        translation_key="steps",
        native_unit_of_measurement="steps",
        state_class=SensorStateClass.TOTAL_INCREASING,
        icon="mdi:shoe-print",
        value_fn=_get_steps,
    ),
    One2TrackSensorDescription(
        key="accuracy",
        translation_key="accuracy",
        native_unit_of_measurement=UnitOfLength.METERS,
        device_class=SensorDeviceClass.DISTANCE,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:crosshairs-gps",
        value_fn=_get_accuracy,
    ),
    One2TrackSensorDescription(
        key="status",
        translation_key="status",
        device_class=SensorDeviceClass.ENUM,
        options=["gps", "wifi", "offline"],
        icon="mdi:access-point-network",
        value_fn=_get_status,
    ),
]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up One2Track sensor entities."""
    coordinator: GpsCoordinator = hass.data[DOMAIN][entry.entry_id]['coordinator']

    devices: list[TrackerDevice] = coordinator.data or []

    entities = []
    for device in devices:
        for description in SENSOR_DESCRIPTIONS:
            entities.append(
                One2TrackSensorEntity(coordinator, device, description)
            )

    async_add_entities(entities)


class One2TrackSensorEntity(CoordinatorEntity, SensorEntity):
    """A sensor entity for One2Track device data."""

    entity_description: One2TrackSensorDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: GpsCoordinator,
        device: TrackerDevice,
        description: One2TrackSensorDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._device = device
        self._attr_unique_id = f"{device['uuid']}_{description.key}"

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self._device['uuid'])},
            serial_number=self._device['serial_number'],
            name=self._device['name'],
        )

    @property
    def native_value(self) -> Any:
        return self.entity_description.value_fn(self._device)

    @callback
    def _handle_coordinator_update(self) -> None:
        new_data: list[TrackerDevice] = self.coordinator.data
        if new_data:
            me = next((x for x in new_data if x['uuid'] == self._device['uuid']), None)
            if me:
                self._device = me
                self.async_write_ha_state()
