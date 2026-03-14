import logging

import voluptuous as vol
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import entity_registry as er

from .client import GpsClient, TrackerDevice
from .common import DOMAIN
from .coordinator import GpsCoordinator

LOGGER = logging.getLogger(__name__)

SERVICE_SEND_MESSAGE = "send_message"
SERVICE_FORCE_UPDATE = "force_update"
ATTR_MESSAGE = "message"


def _resolve_device_uuid(hass: HomeAssistant, entity_ids: list[str]) -> str:
    """Resolve a target entity ID to a One2Track device UUID."""
    if not entity_ids:
        raise HomeAssistantError("No target entity specified")

    registry = er.async_get(hass)

    for entity_id in entity_ids:
        entry = registry.async_get(entity_id)
        if entry and entry.platform == DOMAIN:
            unique_id = entry.unique_id
            for entry_data in hass.data.get(DOMAIN, {}).values():
                if not isinstance(entry_data, dict):
                    continue
                coordinator = entry_data.get("coordinator")
                if coordinator and coordinator.data:
                    for device in coordinator.data:
                        if unique_id == device.get("uuid") or unique_id.startswith(device.get("uuid", "") + "_"):
                            return device["uuid"]
            return unique_id

    raise HomeAssistantError(f"Could not resolve One2Track device from {entity_ids}")


def _get_client_for_uuid(hass: HomeAssistant, device_uuid: str) -> GpsClient:
    """Find the API client that manages a given device UUID."""
    for entry_data in hass.data.get(DOMAIN, {}).values():
        if not isinstance(entry_data, dict):
            continue
        coordinator: GpsCoordinator = entry_data.get("coordinator")
        if coordinator and coordinator.data:
            devices: list[TrackerDevice] = coordinator.data
            for device in devices:
                if device.get("uuid") == device_uuid:
                    return entry_data["api_client"]

    raise HomeAssistantError(f"No One2Track client found for device {device_uuid}")


async def async_setup_services(hass: HomeAssistant) -> None:
    """Set up One2Track services."""
    if hass.services.has_service(DOMAIN, SERVICE_SEND_MESSAGE):
        return

    async def handle_send_message(call: ServiceCall) -> None:
        entity_ids = call.data.get("entity_id", [])
        if isinstance(entity_ids, str):
            entity_ids = [entity_ids]

        message = call.data[ATTR_MESSAGE]
        device_uuid = _resolve_device_uuid(hass, entity_ids)
        client = _get_client_for_uuid(hass, device_uuid)

        LOGGER.info("Sending message to %s: %s", device_uuid, message)
        success = await client.send_message(device_uuid, message)
        if not success:
            raise HomeAssistantError("Failed to send message to One2Track device")

    async def handle_force_update(call: ServiceCall) -> None:
        entity_ids = call.data.get("entity_id", [])
        if isinstance(entity_ids, str):
            entity_ids = [entity_ids]

        device_uuid = _resolve_device_uuid(hass, entity_ids)
        client = _get_client_for_uuid(hass, device_uuid)

        LOGGER.info("Requesting force update for %s", device_uuid)
        success = await client.force_update(device_uuid)
        if not success:
            raise HomeAssistantError("Failed to activate positioning mode on One2Track device")

        for entry_data in hass.data.get(DOMAIN, {}).values():
            if not isinstance(entry_data, dict):
                continue
            coordinator: GpsCoordinator = entry_data.get("coordinator")
            if coordinator:
                await coordinator.async_request_refresh()

    hass.services.async_register(
        DOMAIN,
        SERVICE_SEND_MESSAGE,
        handle_send_message,
        schema=vol.Schema({
            vol.Required("entity_id"): vol.Any(str, [str]),
            vol.Required(ATTR_MESSAGE): str,
        }),
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_FORCE_UPDATE,
        handle_force_update,
        schema=vol.Schema({
            vol.Required("entity_id"): vol.Any(str, [str]),
        }),
    )


async def async_unload_services(hass: HomeAssistant) -> None:
    """Unload One2Track services."""
    hass.services.async_remove(DOMAIN, SERVICE_SEND_MESSAGE)
    hass.services.async_remove(DOMAIN, SERVICE_FORCE_UPDATE)
