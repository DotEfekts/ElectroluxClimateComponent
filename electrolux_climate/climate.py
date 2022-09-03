import json
import typing as t
import base64
import json

import broadlink

from .electrolux import electrolux, create_from_device

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN

from broadlink.const import DEFAULT_TIMEOUT
from broadlink.exceptions import AuthenticationError, NetworkTimeoutError, BroadlinkException


from homeassistant.components.climate.const import FAN_AUTO, FAN_HIGH, FAN_LOW, FAN_MEDIUM, FAN_OFF, SWING_OFF, SWING_VERTICAL, ClimateEntityFeature, HVACMode
from homeassistant.components.climate import ClimateEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.const import TEMP_CELSIUS

from .const import FAN_QUIET, FAN_TURBO, MAX_TEMP, MIN_TEMP

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, add_entities_async) -> bool:
    """Set up Electrolux Control from a config entry."""

    hass.data.setdefault(DOMAIN, {})

    host = entry.data["ip"]
    port = entry.data["port"]
    mac = base64.b64decode(entry.data["mac"])
    name = entry.title
    sn = ""

    discovery = broadlink.discover(discover_ip_address=host, discover_ip_port=port)
    
    if len(discovery) > 0 and discovery[0].devtype == 0x4f9b:
        sn = json.loads(create_from_device(discovery[0]).get_status())["sn"]

    if sn == "":
        return False

    device = ElectroluxClimateEntity(hass, entry, sn, name, (host, port), mac)
    await device.async_setup()

    add_entities_async([device], True)

    return True


class ElectroluxClimateEntity(ClimateEntity):

    def __init__(self, 
        hass: HomeAssistant,
        config: ConfigEntry,
        sn: str,
        name: str,
        host: t.Tuple[str, int],
        mac: t.Union[bytes, str]):
        super().__init__()
        self.hass = hass
        self.config = config

        self.host = host
        self.mac = mac

        self.sn = sn
        self._attr_unique_id = sn
        self._attr_name = name

        self._attr_temperature_unit = TEMP_CELSIUS
        self._attr_precision = 1
        self._attr_target_temperature_step = 1
        self._attr_max_temp = MAX_TEMP
        self._attr_min_temp = MIN_TEMP
        self._attr_hvac_mode = HVACMode.OFF
        self._attr_hvac_modes = [HVACMode.OFF, HVACMode.AUTO, HVACMode.HEAT, HVACMode.COOL, HVACMode.DRY, HVACMode.FAN_ONLY]
        self._attr_fan_mode = FAN_OFF
        self._attr_fan_modes = [FAN_AUTO, FAN_LOW, FAN_MEDIUM, FAN_HIGH, FAN_QUIET, FAN_TURBO]
        self._attr_swing_mode = SWING_OFF
        self._attr_swing_modes = [SWING_OFF, SWING_VERTICAL]
        self._attr_supported_features = ClimateEntityFeature.FAN_MODE | ClimateEntityFeature.SWING_MODE | ClimateEntityFeature.TARGET_TEMPERATURE

    def convert_to_hvacmode(self, state: int) -> str:
        match state:
            case electrolux.mode.AUTO.value: 
                return HVACMode.AUTO
            case electrolux.mode.COOL.value: 
                return HVACMode.COOL
            case electrolux.mode.HEAT.value | electrolux.mode.HEAT_8.value: 
                return HVACMode.HEAT
            case electrolux.mode.DRY.value: 
                return HVACMode.DRY
            case electrolux.mode.FAN.value: 
                return HVACMode.FAN_ONLY
            case _:
                return HVACMode.AUTO

    def convert_to_fanmode(self, state: int) -> str:
        match state:
            case electrolux.fan.AUTO.value: 
                return FAN_AUTO
            case electrolux.fan.LOW.value: 
                return FAN_LOW
            case electrolux.fan.MID.value: 
                return FAN_MEDIUM
            case electrolux.fan.HIGH.value: 
                return FAN_HIGH
            case electrolux.fan.TURBO.value: 
                return FAN_TURBO
            case electrolux.fan.QUIET.value: 
                return FAN_QUIET
            case _:
                return FAN_AUTO

    def update(self):
        state = json.loads(self.device.get_status())
        if state["sn"] != self.sn:
            self._attr_available = False
            return
        self._attr_available = True
        self._attr_current_temperature = state['envtemp']
        self._attr_target_temperature = state['temp']
        self._attr_hvac_mode = HVACMode.OFF if state['ac_pwr'] == 0 else self.convert_to_hvacmode(state['ac_mode'])
        self._attr_fan_mode = self.convert_to_fanmode(state['ac_mark'])
        self._attr_swing_mode = SWING_OFF if state['ac_vdir'] == 0 else SWING_VERTICAL

    def turn_on(self):
        self.device.set_power(True)

    def turn_off(self):
        self.device.set_power(False)

    def convert_to_ele_mode(self, mode: HVACMode) -> electrolux.mode:
        match mode:
            case HVACMode.AUTO: 
                return electrolux.mode.AUTO
            case HVACMode.HEAT: 
                return electrolux.mode.HEAT
            case HVACMode.COOL: 
                return electrolux.mode.COOL
            case HVACMode.DRY: 
                return electrolux.mode.DRY
            case HVACMode.FAN_ONLY: 
                return electrolux.mode.FAN
            case _:
                return electrolux.mode.AUTO

    def set_hvac_mode(self, hvac_mode):
        if hvac_mode == HVACMode.OFF and self.hvac_mode != HVACMode.OFF:
            self.device.set_power(False)
        if hvac_mode != HVACMode.OFF:
            if self.hvac_mode == HVACMode.OFF:
                self.device.set_power(True)
            self.device.set_mode(self.convert_to_ele_mode(hvac_mode))

    def convert_to_ele_fan(self, fan_mode: t.Literal) -> electrolux.fan:
        if fan_mode == FAN_AUTO:
            return electrolux.fan.AUTO
        if fan_mode == FAN_LOW:
            return electrolux.fan.LOW
        if fan_mode == FAN_MEDIUM:
            return electrolux.fan.MID
        if fan_mode == FAN_HIGH:
            return electrolux.fan.HIGH
        if fan_mode == FAN_TURBO:
            return electrolux.fan.TURBO
        if fan_mode == FAN_QUIET:
            return electrolux.fan.QUIET
        return electrolux.fan.AUTO

    def set_fan_mode(self, fan_mode):
        self.device.set_fan(self.convert_to_ele_fan(fan_mode))

    def set_swing_mode(self, swing_mode):
        self.device.set_swing(True if swing_mode == SWING_VERTICAL else False)

    def set_temperature(self, **kwargs):
        if isinstance(kwargs["temperature"], float):
            self.device.set_temp(int(kwargs["temperature"]))

    async def async_setup(self):
        """Set up the device and related entities."""
        
        self.device = electrolux(
            self.host, 
            self.mac, 
            0x4f9b, 
            DEFAULT_TIMEOUT, 
            self.name, 
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

        self.hass.data[DOMAIN][self.config.entry_id] = self

        return True
