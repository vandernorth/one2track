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


async def install_first_login(username, password) -> List[TrackerDevice]:
    config = One2TrackConfig(username=username, password=password)
    client = get_client(config)
    account_id = await client.install()
    return account_id


class One2TrackConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):

    # For future migration support
    VERSION = 1

    def __init__(self) -> None:
        self._prefix = DEFAULT_PREFIX

    async def async_step_user(self, user_input=None):
        errors = {}
        user_input = user_input or {}
        if user_input:
            try:
                account_id = await install_first_login(
                    user_input[CONF_USER_NAME],
                    user_input[CONF_PASSWORD]
                )

                _LOGGER.info(
                    f"One2Track GPS: Found account: {account_id}"
                )

                user_input[CONF_ID] = account_id
                await self.async_set_unique_id(user_input[CONF_ID])
                self._abort_if_unique_id_configured()

                return self.async_create_entry(
                    title=f"{user_input[CONF_USER_NAME]}/{user_input[CONF_ID]}",
                    data=user_input,
                )
            except AuthenticationError:
                errors["base"] = "authentication_error"

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_USER_NAME): cv.string,
                    vol.Required(CONF_PASSWORD): cv.string
                }
            ),
            errors=errors,
        )
