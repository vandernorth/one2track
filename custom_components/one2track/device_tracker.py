import logging
from typing import List

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.components.zone import async_active_zone
from homeassistant.components.device_tracker.config_entry import TrackerEntity
from homeassistant.core import callback
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
    """Add an entry."""
    LOGGER.debug("one2track async_setup_entry")

    coordinator: GpsCoordinator = hass.data[DOMAIN][entry.entry_id]['coordinator']

    await coordinator.async_config_entry_first_refresh()

    devices: List[TrackerDevice] = coordinator.data or []

    LOGGER.info("Adding %s found one2track devices", len(devices))

    async_add_entities(
        [
            One2TrackSensor(coordinator, hass, entry, device)
            for device in devices
        ],
        update_before_add=False,
    )

    LOGGER.debug("Done adding all trackers.")


class One2TrackSensor(CoordinatorEntity, TrackerEntity):
    _device: TrackerDevice

    def __init__(
            self,
            coordinator: GpsCoordinator,
            hass: HomeAssistant,
            entry: ConfigEntry,
            device: TrackerDevice
    ) -> None:
        super().__init__(coordinator)
        self._hass = hass
        self._entry = entry
        self._device = device
        self._attr_unique_id = device['uuid']
        self._attr_name = f"one2track_{device['name']}"

    @property
    def name(self):
        """Return the name of the device."""
        return self._device['name']

    @property
    def source_type(self):
        """Return the source type, eg gps or router, of the device."""
        return "gps"

    @property
    def location_accuracy(self):
        """Return the gps accuracy of the device in meters."""
        meta = self._device.get('last_location', {}).get('meta_data')
        if meta and 'accuracy_meters' in meta:
            return meta['accuracy_meters']
        return 10

    @property
    def should_poll(self):
        return False

    @property
    def device_info(self):
        """Return the device_info of the device."""
        return {
            "identifiers": {(DOMAIN, self.unique_id)},
            "serial_number": self._device['serial_number'],
            "name": self._device['name']
        }

    @property
    def icon(self):
        return "mdi:watch-variant"

    @property
    def extra_state_attributes(self):
        """Return device specific attributes."""
        return {
            "serial_number": self._device['serial_number'],
            "uuid": self._device['uuid'],
            "name": self._device['name'],

            "status": self._device['status'],
            "phone_number": self._device['phone_number'],
            "tariff_type": self._device['simcard']['tariff_type'],
            "balance_cents": self._device['simcard']['balance_cents'],

            "last_communication": self._device['last_location']['last_communication'],
            "last_location_update": self._device['last_location']['last_location_update'],
            "altitude": self._device['last_location']['altitude'],
            "location_type": self._device['last_location']['location_type'],
            "address": self._device['last_location']['address'],
            "signal_strength": self._device['last_location']['signal_strength'],
            "satellite_count": self._device['last_location']['satellite_count'],
            "host": self._device['last_location']['host'],
            "port": self._device['last_location']['port'],
        }

    @property
    def battery_level(self):
        """Return battery value of the device."""
        return self._device["last_location"]["battery_percentage"]

    @property
    def location_name(self):
        """Return a location name for the current location of the device."""
        if self._device["last_location"]["location_type"] == 'WIFI':
            return 'home'

        try:
            zone_name = async_active_zone(self._hass, self.latitude, self.longitude, 0)
            if zone_name:
                return zone_name.name
        except Exception as err:
            LOGGER.error(f"Cannot get zone for tracker: {err}")

        return self._device['last_location']['address']

    @property
    def latitude(self):
        """Return latitude value of the device."""
        return float(self._device['last_location']['latitude'])

    @property
    def longitude(self):
        """Return longitude value of the device."""
        return float(self._device['last_location']['longitude'])

    @property
    def unique_id(self):
        """Return the unique ID."""
        return self._device['uuid']

    async def async_added_to_hass(self):
        """Register state update callback."""
        await super().async_added_to_hass()

    async def async_will_remove_from_hass(self):
        """Clean up after entity before removal."""
        await super().async_will_remove_from_hass()

    @callback
    def _update_from_latest_data(self) -> None:
        """Update the entity from the latest data."""
        new_data: List[TrackerDevice] = self.coordinator.data
        me = next((x for x in new_data if x['uuid'] == self.unique_id), None)
        if me:
            self._device = me
        else:
            LOGGER.error(f"Tracker {self.unique_id} not found in new data: {new_data}")

    @callback
    def _handle_coordinator_update(self) -> None:
        """Respond to a DataUpdateCoordinator update."""
        self._update_from_latest_data()
        self.async_write_ha_state()
