import asyncio
import aiohttp
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.components.device_tracker import DOMAIN as DEVICE_TRACKER
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import device_registry as dr
import voluptuous as vol

from .client import get_client, One2TrackConfig
from .common import (
    CONF_USER_NAME,
    CONF_PASSWORD,
    CONF_ID,
    DOMAIN,
    LOGGER
)

PLATFORMS = [DEVICE_TRACKER]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up One2Track Data from a config entry."""

    if not DOMAIN in hass.data:
        hass.data[DOMAIN] = {}

    config = One2TrackConfig(username=entry.data[CONF_USER_NAME], password=entry.data[CONF_PASSWORD], id=entry.data[CONF_ID])
    api = get_client(config)
    try:
        #would not work in devcontainer with latest ha core
        #account_id = await (await hass.async_add_executor_job(api.install))
        account_id = await api.install()
    except (aiohttp.ClientError, TimeoutError) as ex:
        LOGGER.error("Could not retrieve details from One2Track API")
        raise ConfigEntryNotReady from ex

    if account_id != entry.data[CONF_ID]:
        LOGGER.error(f"Unexpected initial account id: {account_id}. Expected: {entry.data[CONF_ID]}")
        raise ConfigEntryNotReady

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {'api_client': api}


    def get_device(hass, device_id):
        # Get the device registry
        dev_registry =  dr.async_get(hass)

        # Find the device in the registry
        device = dev_registry.async_get(device_id)

        return device

    def get_uuid_from_device(device):
        # This function assumes each device has exactly one identifier tuple
        # Adjust accordingly if there might be multiple
        for identifier in device.identifiers:
            if identifier[0] == 'one2track':
                return identifier[1]
        return None  # Return None if no matching identifier is found

    # Register the service
    async def handle_send_device_command(call):
        """Handle the service call to send_device_command."""
        device_id   = call.data.get("device_id")
        cmd_code    = call.data.get("cmd_code")
        cmd_value   = call.data.get("cmd_value")
        cmd_value_param   = call.data.get("cmd_value_param")
        api_client  = hass.data[DOMAIN][entry.entry_id]["api_client"]

        device = get_device(hass, device_id)
        uuid = get_uuid_from_device(device)

        LOGGER.debug("handle_send_device_command")
        LOGGER.debug(api_client)

        if api_client:
            await api_client.send_device_command(uuid, cmd_code, cmd_value, cmd_value_param)

    # Register the service with the schema
    hass.services.async_register(
        DOMAIN,
        "send_device_command",
        handle_send_device_command,
        schema=vol.Schema(
            {
                vol.Required("device_id"): cv.string,
                vol.Required("cmd_code"): cv.string,
                vol.Optional("cmd_value"): cv.string,
                vol.Optional("cmd_value_param"): cv.string,
            }
        ),
    )

    # Register the service
    async def handle_send_device_message(call):
        """Handle the service call to send_device_message."""
        device_id   = call.data.get("device_id")
        message     = call.data.get("message")
        api_client  = hass.data[DOMAIN][entry.entry_id]["api_client"]

        device = get_device(hass, device_id)
        uuid = get_uuid_from_device(device)

        LOGGER.debug("handle_send_device_message")
        LOGGER.debug(api_client)

        if api_client:
            await api_client.send_device_message(uuid, message)

    # Register the service with the schema
    hass.services.async_register(
        DOMAIN,
        "send_device_message",
        handle_send_device_message,
        schema=vol.Schema(
            {
                vol.Required("device_id"): cv.string,
                vol.Required("message"): cv.string,
            }
        ),
    )

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
