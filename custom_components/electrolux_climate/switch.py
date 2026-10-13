import json
import logging

import broadlink

from .electrolux import electrolux, create_from_device, DEVICE_TYPE

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr

from .const import DOMAIN

from broadlink.const import DEFAULT_TIMEOUT
from broadlink.exceptions import (
    AuthenticationError,
    NetworkTimeoutError,
    BroadlinkException,
)

from homeassistant.components.switch import SwitchEntity
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.const import CONF_HOST, CONF_MAC, CONF_NAME

logger = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, add_entities_async
) -> bool:
    """Set up Electrolux Control from a config entry."""

    hass.data.setdefault(DOMAIN, {})

    host = entry.data[CONF_HOST]
    mac = bytes.fromhex(entry.data[CONF_MAC])
    name = entry.title
    sn = ""

    discovery = await broadlink.discover(discover_ip_address=host)

    if len(discovery) > 0 and discovery[0].devtype == 0x4F9B:
        device = create_from_device(discovery[0])
        status_raw = await device.get_status()
        status_json = json.loads(status_raw)
        logger.info(status_json)

        if "sn" in status_json:
            sn = status_json["sn"]
        else:
            sn = mac.hex()

    if sn == "":
        return False

    led_dev = ElectroluxClimateLedEntity(
        hass,
        entry,
        sn,
        name,
        entry.data[CONF_NAME],
        (host, broadlink.DEFAULT_PORT),
        mac,
    )
    await led_dev.async_setup()

    add_entities_async([led_dev], True)

    return True


class ElectroluxClimateLedEntity(SwitchEntity):
    """Entity for controlling the LED state of an Electrolux device."""

    def __init__(
        self,
        hass: HomeAssistant,
        config: ConfigEntry,
        sn: str,
        name: str,
        dev_name: str,
        host: tuple[str, int],
        mac: bytes | str,
    ) -> None:
        """Entity constructor."""
        super().__init__()
        self.hass = hass
        self.config = config

        self.host = host
        self.mac = mac

        self.sn = sn
        self._attr_unique_id = sn + "-led"  # mac.hex().lower().replace(":", "")
        self._attr_name = name + " LED"
        self.dev_name = dev_name + " LED"
        self.device: electrolux

    async def async_update(self):
        """Fetch the current state from the device."""
        raw_status = await self.device.get_status()
        state = json.loads(raw_status)
        self._attr_available = "scrdisp" in state
        self._attr_is_on = state.get("scrdisp") == 1

    async def async_turn_on(self):
        """Turn the device LED on."""
        await self.device.set_led(True)

    async def async_turn_off(self):
        """Turn the device LED off."""
        await self.device.set_led(False)

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
            False,
        )

        try:
            await self.device.auth()

        except AuthenticationError:
            return False

        except (NetworkTimeoutError, OSError) as err:
            raise ConfigEntryNotReady from err

        except BroadlinkException:
            return False

        return True

    @property
    def device_info(self) -> dr.DeviceInfo:
        """Return device info."""
        return dr.DeviceInfo(
            connections={(dr.CONNECTION_NETWORK_MAC, self.mac.hex())},
            identifiers={(DOMAIN, self._attr_unique_id)},
            name=self.name,
        )
