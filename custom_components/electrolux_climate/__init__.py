"""The Electrolux Control integration."""
import base64

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry

from homeassistant.const import CONF_HOST, CONF_TIMEOUT, CONF_NAME, CONF_MAC
from homeassistant.components.climate.const import ATTR_MAX_TEMP, ATTR_MIN_TEMP

from broadlink import DEFAULT_TIMEOUT

from .const import PLATFORMS, DEFAULT_MIN, DEFAULT_MAX

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

# Example migration function
async def async_migrate_entry(hass, config_entry: ConfigEntry):
    if config_entry.version == 1:

        config_entry.version = 2

        if "ip" in config_entry.data:
            new = {**config_entry.data}

            new[CONF_NAME] = config_entry.title
            config_entry.title = "ELECTROLUX_OEM"

            new[CONF_HOST] = config_entry.data["ip"]
            new[CONF_MAC] = base64.b64decode(config_entry.data["mac"]).hex()
            new[CONF_TIMEOUT] = DEFAULT_TIMEOUT
            new[ATTR_MIN_TEMP] = DEFAULT_MIN
            new[ATTR_MAX_TEMP] = DEFAULT_MAX

            hass.config_entries.async_update_entry(config_entry, data=new)

    return True