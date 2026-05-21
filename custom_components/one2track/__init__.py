from aiohttp import ClientError
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from .client import AuthenticationError, GpsClient, One2TrackConfig, get_client
from .common import CONF_ID, CONF_PASSWORD, CONF_USER_NAME, DOMAIN, LOGGER
from .coordinator import GpsCoordinator
from .services import async_setup_services, async_unload_services

PLATFORMS = [Platform.DEVICE_TRACKER, Platform.SENSOR, Platform.BINARY_SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up One2Track Data from a config entry."""

    config = One2TrackConfig(
        username=entry.data[CONF_USER_NAME],
        password=entry.data[CONF_PASSWORD],
        id=entry.data[CONF_ID],
    )
    api = get_client(config)
    try:
        account_id = await api.install()
    except (ClientError, AuthenticationError) as ex:
        LOGGER.error("Could not retrieve details from One2Track API")
        raise ConfigEntryNotReady from ex

    if account_id != entry.data[CONF_ID]:
        LOGGER.error(
            "Unexpected initial account id: %s. Expected: %s",
            account_id,
            entry.data[CONF_ID],
        )
        raise ConfigEntryNotReady

    coordinator = GpsCoordinator(hass, api)
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {
        "api_client": api,
        "coordinator": coordinator,
    }

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    await async_setup_services(hass)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        entry_data = hass.data[DOMAIN].pop(entry.entry_id)
        client: GpsClient = entry_data.get("api_client")
        if client and hasattr(client, "session"):
            await client.session.close()
        if not hass.data[DOMAIN]:
            await async_unload_services(hass)

    return unload_ok
