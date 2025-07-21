import asyncio
from requests import ConnectTimeout, HTTPError
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.components.device_tracker import DOMAIN as DEVICE_TRACKER

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
        account_id = await (await hass.async_add_executor_job(api.install))
    except (ConnectTimeout, HTTPError) as ex:
        LOGGER.error("Could not retrieve details from One2Track API")
        raise ConfigEntryNotReady from ex

    if account_id != entry.data[CONF_ID]:
        LOGGER.error(f"Unexpected initial account id: {account_id}. Expected: {entry.data[CONF_ID]}")
        raise ConfigEntryNotReady

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {'api_client': api}

    # for component in PLATFORMS:
        # LOGGER.debug(f"[one2track] creating tracker for: {entry}")
        # await hass.async_create_task(
        #     hass.config_entries.async_forward_entry_setup(entry, component)
        # )
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Unload a config entry."""
    unload_ok = all(
        await asyncio.gather(
            *[
                hass.config_entries.async_forward_entry_unload(entry, component)
                for component in PLATFORMS
            ]
        )
    )
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
