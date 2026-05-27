import logging

import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from homeassistant import config_entries

from .client import AuthenticationError, One2TrackConfig, get_client
from .common import CONF_ID, CONF_PASSWORD, CONF_USER_NAME, DOMAIN

_LOGGER = logging.getLogger(__name__)


class One2TrackConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors = {}
        user_input = user_input or {}
        if user_input:
            client = None
            try:
                config = One2TrackConfig(
                    username=user_input[CONF_USER_NAME],
                    password=user_input[CONF_PASSWORD],
                )
                client = get_client(config)
                account_id = await client.install()

                _LOGGER.info("One2Track GPS: Found account: %s", account_id)

                user_input[CONF_ID] = account_id
                await self.async_set_unique_id(user_input[CONF_ID])
                self._abort_if_unique_id_configured()

                return self.async_create_entry(
                    title=f"{user_input[CONF_USER_NAME]}/{user_input[CONF_ID]}",
                    data=user_input,
                )
            except AuthenticationError:
                errors["base"] = "authentication_error"
            finally:
                if client and hasattr(client, "session"):
                    await client.session.close()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {vol.Required(CONF_USER_NAME): cv.string, vol.Required(CONF_PASSWORD): cv.string}
            ),
            errors=errors,
        )
