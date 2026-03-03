import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.components.zone import async_active_zone
from homeassistant.components.device_tracker.config_entry import TrackerEntity
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

    devices: list[TrackerDevice] = coordinator.data or []

    LOGGER.info("Adding %s found one2track devices", len(devices))

    async_add_entities(
        [
            One2TrackDeviceTracker(coordinator, hass, device)
            for device in devices
        ],
        update_before_add=False,
    )

    LOGGER.debug("Done adding all trackers.")


class One2TrackDeviceTracker(CoordinatorEntity, TrackerEntity):
    _device: TrackerDevice

    def __init__(
            self,
            coordinator: GpsCoordinator,
            hass: HomeAssistant,
            device: TrackerDevice
    ) -> None:
        super().__init__(coordinator)
        self._hass = hass
        self._device = device
        self._attr_unique_id = device['uuid']

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
    def device_info(self) -> DeviceInfo:
        """Return the device_info of the device."""
        return DeviceInfo(
            identifiers={(DOMAIN, self._device['uuid'])},
            serial_number=self._device['serial_number'],
            name=self._device['name'],
        )

    @property
    def icon(self):
        return "mdi:watch-variant"

    @property
    def extra_state_attributes(self):
        """Return device specific attributes."""
        location = self._device.get('last_location', {})
        simcard = self._device.get('simcard', {})
        return {
            "serial_number": self._device.get('serial_number'),
            "uuid": self._device.get('uuid'),
            "name": self._device.get('name'),

            "status": self._device.get('status'),
            "phone_number": self._device.get('phone_number'),
            "tariff_type": simcard.get('tariff_type'),
            "balance_cents": simcard.get('balance_cents'),

            "last_communication": location.get('last_communication'),
            "last_location_update": location.get('last_location_update'),
            "altitude": location.get('altitude'),
            "location_type": location.get('location_type'),
            "address": location.get('address'),
            "signal_strength": location.get('signal_strength'),
            "satellite_count": location.get('satellite_count'),
            "host": location.get('host'),
            "port": location.get('port'),
        }

    @property
    def battery_level(self):
        """Return battery value of the device."""
        return self._device.get("last_location", {}).get("battery_percentage")

    @property
    def location_name(self):
        """Return a location name for the current location of the device."""
        try:
            if self.latitude is not None and self.longitude is not None:
                zone_name = async_active_zone(
                    self._hass, self.latitude, self.longitude, self.location_accuracy
                )
                if zone_name:
                    return zone_name.name
        except Exception as err:
            LOGGER.error("Cannot get zone for tracker: %s", err)

        return self._device.get('last_location', {}).get('address')

    @property
    def latitude(self):
        """Return latitude value of the device."""
        val = self._device.get('last_location', {}).get('latitude')
        if val is not None:
            try:
                return float(val)
            except (ValueError, TypeError):
                return None
        return None

    @property
    def longitude(self):
        """Return longitude value of the device."""
        val = self._device.get('last_location', {}).get('longitude')
        if val is not None:
            try:
                return float(val)
            except (ValueError, TypeError):
                return None
        return None

    @property
    def unique_id(self):
        """Return the unique ID."""
        return self._device['uuid']

    @callback
    def _handle_coordinator_update(self) -> None:
        """Respond to a DataUpdateCoordinator update."""
        new_data: list[TrackerDevice] = self.coordinator.data
        if new_data:
            me = next((x for x in new_data if x['uuid'] == self.unique_id), None)
            if me:
                self._device = me
            else:
                LOGGER.error("Tracker %s not found in new data", self.unique_id)
        self.async_write_ha_state()
