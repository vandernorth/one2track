from aiohttp import ClientError
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.const import Platform
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .client import get_client, One2TrackConfig, AuthenticationError
from .common import (
    CONF_USER_NAME,
    CONF_PASSWORD,
    CONF_ID,
    DOMAIN,
    LOGGER
)
from .coordinator import GpsCoordinator

PLATFORMS = [Platform.DEVICE_TRACKER]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up One2Track Data from a config entry."""

    session = async_get_clientsession(hass)
    config = One2TrackConfig(username=entry.data[CONF_USER_NAME], password=entry.data[CONF_PASSWORD], id=entry.data[CONF_ID])
    api = get_client(config, session)
    try:
        account_id = await api.install()
    except (ClientError, AuthenticationError) as ex:
        LOGGER.error("Could not retrieve details from One2Track API")
        raise ConfigEntryNotReady from ex

    if account_id != entry.data[CONF_ID]:
        LOGGER.error("Unexpected initial account id: %s. Expected: %s", account_id, entry.data[CONF_ID])
        raise ConfigEntryNotReady

    coordinator = GpsCoordinator(hass, api)
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {
        'api_client': api,
        'coordinator': coordinator,
    }

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
