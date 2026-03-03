import asyncio
import logging
from datetime import timedelta

from aiohttp import ClientError
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)
from homeassistant.util import dt as dt_util

from .client import GpsClient, AuthenticationError
from .common import DEFAULT_UPDATE_RATE_MIN

LOGGER = logging.getLogger(__name__)


class GpsCoordinator(DataUpdateCoordinator):
    def __init__(self, hass: HomeAssistant, gps_api: GpsClient):
        super().__init__(
            hass,
            LOGGER,
            name="One2Track",
            update_interval=timedelta(minutes=DEFAULT_UPDATE_RATE_MIN),
            always_update=False
        )
        self.gps_api = gps_api
        self.last_update = None

    async def _async_update_data(self):
        """Fetch data from API endpoint."""
        try:
            async with asyncio.timeout(30):
                data = await self.gps_api.update()

                LOGGER.debug("Update from the coordinator %s", data)
                self.last_update = dt_util.utcnow()
                return data

        except (ClientError, AuthenticationError, TimeoutError) as err:
            LOGGER.error("Error updating from One2Track API: %s", err)
            raise UpdateFailed(err)
