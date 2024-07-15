from typing import List

from homeassistant import config_entries
from .common import (
    DOMAIN,
    DEFAULT_PREFIX,
    CONF_USER_NAME,
    CONF_PASSWORD,
    CONF_ID
)
import voluptuous as vol
import homeassistant.helpers.config_validation as cv
import logging

from custom_components.one2track.client import (
    One2TrackConfig,
    TrackerDevice,
    AuthenticationError
)
from custom_components.one2track.client import get_client


_LOGGER = logging.getLogger(__name__)


async def get_device(username, password, id) -> List[TrackerDevice]:
    config = One2TrackConfig(username=username, password=password, id=id)
    client = get_client(config)
    devices = await client.update()
    return devices


class One2TrackConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):

    # For future migration support
    VERSION = 1

    def __init__(self) -> None:
        """Initialize flow."""
        _LOGGER.warning('started flow')
        self._prefix = DEFAULT_PREFIX

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}
        user_input = user_input or {}
        _LOGGER.warning('go user input')
        if user_input:
            try:
                devices: List[TrackerDevice] = await get_device(
                    user_input[CONF_USER_NAME],
                    user_input[CONF_PASSWORD],
                    user_input[CONF_ID]
                )

                _LOGGER.info(
                    f"One2Track GPS: Found devices {len(devices)}"
                )

                await self.async_set_unique_id(user_input[CONF_ID])
                self._abort_if_unique_id_configured()

                return self.async_create_entry(
                    title=f"one2track-{user_input[CONF_ID]}",
                    data=user_input,
                )
            except AuthenticationError:
                errors["base"] = "authentication_error"

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_USER_NAME): cv.string,
                    vol.Required(CONF_PASSWORD): cv.string,
                    vol.Required(CONF_ID): cv.string
                }
            ),
            errors=errors,
        )
