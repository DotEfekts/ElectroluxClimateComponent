"""Config flow for Electrolux Climate."""
from pickle import NONE
import broadlink
import base64
import voluptuous as vol

from homeassistant import config_entries, data_entry_flow

from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_entry_flow

from broadlink.const import DEFAULT_PORT

from homeassistant.helpers.typing import DiscoveryInfoType

from .const import DOMAIN


async def _async_has_devices(hass: HomeAssistant) -> bool:
    """Return if there are devices that can be discovered."""
    devices = await hass.async_add_executor_job(broadlink.discover)
    supportedDevices = []
    for device in devices:
        if device.devtype == 0x4f9b:
            supportedDevices.append(device)
    return len(supportedDevices) > 0

config_entry_flow.register_discovery_flow(DOMAIN, "Electrolux Climate", _async_has_devices)

class ElectroluxClimateConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    async def async_step_user(self, info) -> data_entry_flow.FlowResult:
        errors = {}
        if info is not None:
            device = broadlink.discover(discover_ip_address=info["ip"])
            if len(device) > 0 and device[0].devtype == 0x4f9b:
                return self.async_create_entry(
                    title="Electrolux Climate", 
                    data={
                        "ip": info["ip"],
                        "port": DEFAULT_PORT,
                        "mac": base64.b64encode(device[0].mac).decode('ascii')
                    })
            else:
                errors["base"] = "not_found"

        return self.async_show_form(
            step_id="user", data_schema=vol.Schema({vol.Required("ip"): str}), errors=errors
        )
    
    async def async_step_integration_discovery(self, discovery_info: DiscoveryInfoType) -> data_entry_flow.FlowResult:
        devices = await self.hass.async_add_executor_job(broadlink.discover)
        lastResult = {}

        for device in devices:
            if device.devtype == 0x4f9b:
                lastResult = self.async_create_entry(
                    title="Electrolux Climate", 
                    data={
                        "ip": device.host[0],
                        "port": DEFAULT_PORT,
                        "mac": base64.b64encode(device.mac).decode('ascii')
                    })

        return lastResult
        