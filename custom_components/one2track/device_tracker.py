import logging
from datetime import timedelta, datetime
from typing import List

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
import async_timeout
from homeassistant.components.device_tracker.config_entry import TrackerEntity
from homeassistant.core import callback
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
    UpdateFailed,
)

from .client import GpsClient, TrackerDevice
from .common import (
    DOMAIN, DEFAULT_UPDATE_RATE_MIN
)

LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
        hass: HomeAssistant,
        entry: ConfigEntry,
        async_add_entities: AddEntitiesCallback,
) -> None:
    """Add an entry."""
    # Add the needed sensors to hass
    LOGGER.debug("one2track async_setup_entry")

    gps_api: GpsClient = hass.data[DOMAIN][entry.entry_id]['api_client']
    devices: List[TrackerDevice] = await gps_api.update()

    coordinator = GpsCoordinator(hass, gps_api, True)

    LOGGER.info("Adding %s found one2track devices", len(devices))

    for device in devices:
        LOGGER.debug("Adding %s", device)
        async_add_entities(
            [
                One2TrackSensor(
                    coordinator,
                    hass,
                    entry,
                    device
                )
            ],
            update_before_add=True,
        )

    LOGGER.debug("Done adding all trackers.")


class GpsCoordinator(DataUpdateCoordinator):
    def __init__(self, hass, gps_api: GpsClient, first_boot):
        super().__init__(
            hass,
            LOGGER,
            # Name of the data. For logging purposes.
            name="One2Track",
            # Polling interval. Will only be polled if there are subscribers.
            update_interval=timedelta(minutes=DEFAULT_UPDATE_RATE_MIN),
            always_update=False
        )
        self.gps_api = gps_api
        self.first_boot = first_boot
        self.last_update = None

    async def _async_update_data(self):
        """Fetch data from API endpoint."""
        try:
            # Note: asyncio.TimeoutError and aiohttp.ClientError are already
            # handled by the data update coordinator.
            async with async_timeout.timeout(300):
                data = await (await self.hass.async_add_executor_job(
                    self.gps_api.update
                ))

                LOGGER.debug("Update from the coordinator %s", data)

                update = True

                if update or self.first_boot:
                    LOGGER.debug("Updating sensor data. Last update: %s", self.last_update)
                    self.last_update = datetime.now()
                    return data
                else:
                    LOGGER.debug("No new data to enter")
                    return None

        except Exception as err:
            LOGGER.error("Error in updating updater")
            LOGGER.error(err)
            raise UpdateFailed(err)


class One2TrackSensor(CoordinatorEntity, TrackerEntity):
    _device: TrackerDevice

    def __init__(
            self,
            coordinator,
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
        return "gps"  # TODO: Could be router when status=WIFI

    def async_device_changed(self):
        """Send changed data to HA"""
        LOGGER.debug("%s (%d) advising HA of update", self.name, self.unique_id)
        self.async_schedule_update_ha_state()

    @property
    def location_accuracy(self):
        """Return the gps accuracy of the device. In accuracy in meters"""
        return 10  # TODO check signal strength

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
        try:
            zone_name = self._hass.components.zone.async_active_zone(self.latitude, self.longitude)
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
