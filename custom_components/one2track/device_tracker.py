import logging
from typing import List

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.entity import DeviceInfo
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
    DOMAIN,
    UPDATE_DELAY
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

    LOGGER.warning("Adding %s found one2track devices", len(devices))

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
            update_interval=UPDATE_DELAY,
        )
        self.gps_api = gps_api
        self.first_boot = first_boot

    async def _async_update_data(self):
        """Fetch data from API endpoint."""
        try:
            # Note: asyncio.TimeoutError and aiohttp.ClientError are already
            # handled by the data update coordinator.
            async with async_timeout.timeout(300):
                LOGGER.debug("Update from the coordinator")
                data = await self.hass.async_add_executor_job(
                    self.gps_api.update
                )

                update = True

                if update or self.first_boot:
                    LOGGER.debug("Updating sensor data")
                    self.first_boot = False
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
        self._attr_unique_id = device['serial_number']
        self._attr_name = f"one2track_{device['name']}"

    @property
    def name(self):
        """Return the name of the device."""
        return self._device['name']

    @property
    def source_type(self):
        """Return the source type, eg gps or router, of the device."""
        return "gps" # TODO: Could be router when status=WIFI

    def async_device_changed(self):
        """Send changed data to HA"""
        LOGGER.debug("%s (%d) advising HA of update", self.name, self.unique_id)
        self.async_schedule_update_ha_state()

    @property
    def location_accuracy(self):
        """Return the gps accuracy of the device."""
        return 100  # TODO check signal strenth

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
        return "mdi:map-marker-radius"

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
        return self._device['last_location']['address']

    @property
    def latitude(self):
        """Return latitude value of the device."""
        return self._device['last_location']['latitude']

    @property
    def longitude(self):
        """Return longitude value of the device."""
        return self._device['last_location']['longitude']

    @property
    def unique_id(self):
        """Return the unique ID."""
        return self._device['uuid']

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""

        self.async_write_ha_state()
