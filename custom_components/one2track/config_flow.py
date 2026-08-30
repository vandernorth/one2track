import logging

import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from aiohttp import ClientError
from homeassistant import config_entries

from .client import AuthenticationError, One2TrackConfig, SiteUnavailableError, get_client
from .common import CONF_ID, CONF_PASSWORD, CONF_USER_NAME, DOMAIN

_LOGGER = logging.getLogger(__name__)


class One2TrackConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    def __init__(self) -> None:
        self._reauth_entry: config_entries.ConfigEntry | None = None

    async def _validate_and_get_account_id(
        self, username: str, password: str
    ) -> tuple[str, dict[str, str]]:
        """Try to authenticate against One2Track; return (account_id, errors)."""
        errors: dict[str, str] = {}
        account_id = ""
        client = None
        try:
            config = One2TrackConfig(username=username, password=password)
            client = get_client(config)
            account_id = await client.install()
            _LOGGER.info("One2Track GPS: Found account: %s", account_id)
        except AuthenticationError:
            errors["base"] = "authentication_error"
        except (SiteUnavailableError, ClientError):
            errors["base"] = "cannot_connect"
        except Exception:  # pragma: no cover - safety net
            _LOGGER.exception("Unexpected error validating One2Track credentials")
            errors["base"] = "unknown"
        finally:
            if client and hasattr(client, "session"):
                await client.session.close()
        return account_id, errors

    async def async_step_user(self, user_input=None):
        errors: dict[str, str] = {}
        user_input = user_input or {}
        if user_input:
            account_id, errors = await self._validate_and_get_account_id(
                user_input[CONF_USER_NAME], user_input[CONF_PASSWORD]
            )
            if not errors:
                user_input[CONF_ID] = account_id
                await self.async_set_unique_id(user_input[CONF_ID])
                self._abort_if_unique_id_configured()

                return self.async_create_entry(
                    title=f"{user_input[CONF_USER_NAME]}/{user_input[CONF_ID]}",
                    data=user_input,
                )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {vol.Required(CONF_USER_NAME): cv.string, vol.Required(CONF_PASSWORD): cv.string}
            ),
            errors=errors,
        )

    async def async_step_reauth(self, entry_data):
        """Handle reauth triggered by ConfigEntryAuthFailed."""
        self._reauth_entry = self.hass.config_entries.async_get_entry(self.context["entry_id"])
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(self, user_input=None):
        errors: dict[str, str] = {}
        if user_input is not None:
            account_id, errors = await self._validate_and_get_account_id(
                self._reauth_entry.data[CONF_USER_NAME], user_input[CONF_PASSWORD]
            )
            if not errors:
                new_data = {**self._reauth_entry.data, CONF_PASSWORD: user_input[CONF_PASSWORD]}
                self.hass.config_entries.async_update_entry(self._reauth_entry, data=new_data)
                await self.hass.config_entries.async_reload(self._reauth_entry.entry_id)
                return self.async_abort(reason="reauth_successful")

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema({vol.Required(CONF_PASSWORD): cv.string}),
            errors=errors,
            description_placeholders={"username": self._reauth_entry.data[CONF_USER_NAME]},
        )
