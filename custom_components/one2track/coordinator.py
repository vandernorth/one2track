import asyncio
import logging
from datetime import timedelta

from aiohttp import ClientError
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)
from homeassistant.util import dt as dt_util

from .client import AuthenticationError, GpsClient, SiteUnavailableError
from .common import BACKOFF_MULTIPLIER, DEFAULT_UPDATE_RATE_MIN, MAX_UPDATE_RATE_MIN

LOGGER = logging.getLogger(__name__)


class GpsCoordinator(DataUpdateCoordinator):
    def __init__(self, hass: HomeAssistant, gps_api: GpsClient):
        super().__init__(
            hass,
            LOGGER,
            name="One2Track",
            update_interval=timedelta(minutes=DEFAULT_UPDATE_RATE_MIN),
            always_update=False,
        )
        self.gps_api = gps_api
        self.last_update = None
        self._consecutive_failures = 0

    async def _async_update_data(self):
        """Fetch data from API endpoint."""
        try:
            async with asyncio.timeout(30):
                data = await self.gps_api.update()

            LOGGER.debug("Update from the coordinator %s", data)
            self.last_update = dt_util.utcnow()
            if self._consecutive_failures:
                LOGGER.info(
                    "One2Track API recovered after %s failed attempt(s)",
                    self._consecutive_failures,
                )
            self._consecutive_failures = 0
            self.update_interval = timedelta(minutes=DEFAULT_UPDATE_RATE_MIN)
            return data

        except AuthenticationError as err:
            # Confirmed bad/expired credentials — trigger HA's native reauth flow.
            LOGGER.error("One2Track authentication failed, reauthentication required: %s", err)
            raise ConfigEntryAuthFailed(f"Authentication failed: {err}") from err

        except (ClientError, SiteUnavailableError, TimeoutError) as err:
            self._consecutive_failures += 1
            if self._consecutive_failures == 1:
                LOGGER.error("Error updating from One2Track API: %s", err)
            else:
                LOGGER.debug(
                    "Error updating from One2Track API (failure #%s): %s",
                    self._consecutive_failures,
                    err,
                )

            backoff_minutes = min(
                DEFAULT_UPDATE_RATE_MIN * (BACKOFF_MULTIPLIER ** (self._consecutive_failures - 1)),
                MAX_UPDATE_RATE_MIN,
            )
            self.update_interval = timedelta(minutes=backoff_minutes)

            raise UpdateFailed(f"Error communicating with API: {err}") from err
