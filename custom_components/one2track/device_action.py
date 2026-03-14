from typing import List, Dict
from homeassistant.core import HomeAssistant
from homeassistant.const import ATTR_DEVICE_ID
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import config_validation as cv

from .common import DOMAIN, LOGGER

import voluptuous as vol

ACTION_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_DEVICE_ID): cv.string,
        vol.Required("entity_id"): cv.string,
        vol.Required("type"): vol.In(["refresh_location"]),
        vol.Optional("domain"): cv.string,  # Only add if 'domain' is intended to be used
    }
)

async def async_get_actions(hass: HomeAssistant, device_id: str) -> List[Dict]:
    """List device actions for One2Track integration."""

    return [
        {
            "device_id": device_id,
            "domain": DOMAIN,
            "entity_id": f"{DOMAIN}.{device_id}",  # Adjust this if necessary to match your entities
            "type": "refresh_location",
        }
    ]


async def async_call_action_from_config(hass: HomeAssistant, config: Dict, variables: Dict, context):
    """Execute the action specified in the configuration."""

    if(config['type'] == 'refresh_location'):

        # Get the device
        device = get_device(hass, config['device_id'])

        #get uuid and entry_id
        uuid = get_uuid_from_device(device)
        entry_id = get_config_entry_id_from_device(device)

        # Extract the api client and device's UUID
        api_client = hass.data[DOMAIN][entry_id]["api_client"]

        if api_client and uuid:
            await api_client.set_device_refresh_location(uuid)
        else:
            LOGGER.error(f"GPS client or UUID not found for device_id: {config['device_id']}")

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

def get_config_entry_id_from_device(device):
    # This function assumes there is at least one config entry ID available
    # It returns the first config entry ID found
    if device.config_entries:
        return next(iter(device.config_entries))
    return None  # Return None if no config entry ID is found

