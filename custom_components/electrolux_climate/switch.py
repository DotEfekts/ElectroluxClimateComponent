import json
import typing as t
import base64
import json
import voluptuous as vol
import homeassistant.helpers.config_validation as cv
import logging

import broadlink

from .electrolux import electrolux, create_from_device, DEVICE_TYPE

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr

from .const import DOMAIN

from broadlink.const import DEFAULT_TIMEOUT
from broadlink.exceptions import AuthenticationError, NetworkTimeoutError, BroadlinkException

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.const import CONF_HOST, CONF_MAC, CONF_NAME


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, add_entities_async) -> bool:
    """Set up Electrolux Control from a config entry."""

    hass.data.setdefault(DOMAIN, {})

    host = entry.data[CONF_HOST]
    mac = bytes.fromhex(entry.data[CONF_MAC])
    name = entry.title
    sn = ""

    discovery = broadlink.discover(discover_ip_address=host)
    
    if len(discovery) > 0 and discovery[0].devtype == 0x4f9b:
        statusJson = json.loads(create_from_device(discovery[0]).get_status())
        logging.info(statusJson)

        if "sn" in statusJson:
            sn = statusJson["sn"]
        else:
            logging.error("SN not available on entry")
            logging.error(statusJson)
            return False

    if sn == "":
        return False

    ledDev = ElectroluxClimateLedEntity(hass, entry, sn, name, entry.data[CONF_NAME], (host, broadlink.DEFAULT_PORT), mac)
    await ledDev.async_setup()

    add_entities_async([ledDev], True)

    return True

class ElectroluxClimateLedEntity(SwitchEntity):

    def __init__(self, 
        hass: HomeAssistant,
        config: ConfigEntry,
        sn: str,
        name: str,
        dev_name: str,
        host: t.Tuple[str, int],
        mac: t.Union[bytes, str]):
        super().__init__()
        self.hass = hass
        self.config = config

        self.host = host
        self.mac = mac

        self.sn = sn
        self._attr_unique_id = sn + "-led" #mac.hex().lower().replace(":", "")
        self._attr_name = name + " LED"
        self.dev_name = dev_name + " LED"

    def update(self):
        state = json.loads(self.device.get_status())
        if state["sn"] != self.sn:
            self._attr_available = False
            return
        self._attr_available = True
        self._attr_is_on = state['scrdisp'] == 1

    def turn_on(self):
        self.device.set_led(True)

    def turn_off(self):
        self.device.set_led(False)

    async def async_setup(self):
        """Set up the device and related entities."""
        
        self.device = electrolux(
            self.host, 
            self.mac, 
            DEVICE_TYPE,
            DEFAULT_TIMEOUT, 
            self.dev_name, 
            "", 
            "Electrolux", 
            False)

        try:
            await self.hass.async_add_executor_job(
                self.device.auth
            )

        except AuthenticationError:
            return False

        except (NetworkTimeoutError, OSError) as err:
            raise ConfigEntryNotReady from err

        except BroadlinkException as err:
            return False

        return True
    
    @property
    def device_info(self) -> dr.DeviceInfo:
        """Return device info."""
        return dr.DeviceInfo(
            connections={(dr.CONNECTION_NETWORK_MAC, self.mac.hex())},
            identifiers={(DOMAIN, self._attr_unique_id)},
            name=self.name
        )
