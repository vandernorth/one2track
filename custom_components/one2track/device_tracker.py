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
        LOGGER.warning("Adding %s", device)
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

                # timetocheck = datetime.now() - CHECK_TIME_DELTA
                # for device in data:
                #     LOGGER.debug(
                #         "Checking time: %s | Versus last measerument: %s",
                #         timetocheck,
                #         device.lastmeasurement,
                #     )
                #
                #     if device.lastmeasurement > timetocheck:
                #         update = True
                #         break

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
    source_type = "gps"
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
        self._attr_name = f"tracker_{device['name']}"

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{entry.entry_id}")},
        )

        # self._attr_native_unit_of_measurement = ""
        # self._attr_device_class = SensorDeviceClass.POWER
        # self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def device_info(self):
        return self._device

    def location_name(self):
        """Return a location name for the current location of the device."""
        return self._device['last_location']['address']

    def latitude(self):
        """Return latitude value of the device."""
        return self._device['last_location']['latitude']

    def longitude(self):
        """Return longitude value of the device."""
        return self._device['last_location']['longitude']

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""

        if self.coordinator.data is not None:
            LOGGER.info(
                "Update the sensor %s - %s with the info from the coordinator",
                self._device['id'],
                self._device['name'],
            )

        self.async_write_ha_state()
