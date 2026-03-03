import logging
from typing import List

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .client import TrackerDevice
from .common import DOMAIN
from .coordinator import GpsCoordinator

LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
        hass: HomeAssistant,
        entry: ConfigEntry,
        async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up One2Track binary sensor entities."""
    coordinator: GpsCoordinator = hass.data[DOMAIN][entry.entry_id]['coordinator']

    devices: List[TrackerDevice] = coordinator.data or []

    async_add_entities(
        [One2TrackTumbleSensor(coordinator, device) for device in devices]
    )


class One2TrackTumbleSensor(CoordinatorEntity, BinarySensorEntity):
    """Binary sensor for tumble/fall detection."""

    _attr_has_entity_name = True
    _attr_translation_key = "tumble"
    _attr_device_class = BinarySensorDeviceClass.SAFETY

    def __init__(
            self,
            coordinator: GpsCoordinator,
            device: TrackerDevice,
    ) -> None:
        super().__init__(coordinator)
        self._device = device
        self._attr_unique_id = f"{device['uuid']}_tumble"

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self._device['uuid'])},
            "serial_number": self._device['serial_number'],
            "name": self._device['name'],
        }

    @property
    def is_on(self) -> bool | None:
        meta = self._device.get("last_location", {}).get("meta_data")
        if meta:
            return meta.get("tumble") == "1"
        return None

    @callback
    def _handle_coordinator_update(self) -> None:
        new_data: List[TrackerDevice] = self.coordinator.data
        if new_data:
            me = next((x for x in new_data if x['uuid'] == self._device['uuid']), None)
            if me:
                self._device = me
        self.async_write_ha_state()
