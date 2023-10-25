"""Config flow for Electrolux Climate."""
from pickle import NONE
import broadlink
import base64
import json
import errno
import socket
import voluptuous as vol
from functools import partial
import homeassistant.helpers.config_validation as cv

from homeassistant import data_entry_flow
from homeassistant.components import dhcp
from homeassistant.config_entries import ConfigFlow
from homeassistant import config_entries

from broadlink.exceptions import (
    NetworkTimeoutError,
)

from .electrolux import DEVICE_TYPE
from .const import DOMAIN, DEFAULT_MIN, DEFAULT_MAX
from homeassistant.const import CONF_HOST, CONF_TIMEOUT, CONF_NAME, CONF_MAC
from homeassistant.components.climate.const import ATTR_MAX_TEMP, ATTR_MIN_TEMP

class ElectroluxClimateConfigFlow(ConfigFlow, domain=DOMAIN):

    VERSION = 2

    def __init__(self):
        self.device = None

    async def async_set_device(self, device, raise_on_progress=True):
        """Define a device for the config flow."""
        if device.devtype != DEVICE_TYPE:
            raise data_entry_flow.AbortFlow("not_supported")

        await self.async_set_unique_id(
            device.mac.hex(), raise_on_progress=raise_on_progress
        )
        self.device = device

        self.context["title_placeholders"] = {
            "name": device.name,
            "model": device.model,
            "host": device.host[0],
        }
            
    async def async_step_dhcp(self, discovery_info: dhcp.DhcpServiceInfo) -> data_entry_flow.FlowResult:
        """Handle dhcp discovery."""

        print('DHCP called')
        host = discovery_info.ip
        unique_id = discovery_info.macaddress.lower().replace(":", "")
        await self.async_set_unique_id(unique_id)
        self._abort_if_unique_id_configured(updates={CONF_HOST: host})

        try:
            device = await self.hass.async_add_executor_job(broadlink.hello, host)

        except NetworkTimeoutError:
            return self.async_abort(reason="cannot_connect")

        except OSError as err:
            if err.errno == errno.ENETUNREACH:
                return self.async_abort(reason="cannot_connect")
            return self.async_abort(reason="unknown")

        if device.devtype != DEVICE_TYPE:
            return self.async_abort(reason="not_supported")

        await self.async_set_device(device)
        return await self.async_step_finish()
    
    async def async_step_user(self, user_input=None):
        """Handle a flow initiated by the user."""
        errors = {}

        if user_input is not None:
            host = user_input[CONF_HOST]

            try:
                hello = partial(broadlink.hello, host)
                device = await self.hass.async_add_executor_job(hello)

            except NetworkTimeoutError:
                errors["base"] = "cannot_connect"

            except OSError as err:
                if err.errno in {errno.EINVAL, socket.EAI_NONAME}:
                    errors["base"] = "invalid_host"
                elif err.errno == errno.ENETUNREACH:
                    errors["base"] = "cannot_connect"
                else:
                    errors["base"] = "unknown"

            else:
                device.timeout = broadlink.DEFAULT_TIMEOUT

                if self.source != config_entries.SOURCE_REAUTH:
                    await self.async_set_device(device)
                    self._abort_if_unique_id_configured(
                        updates={CONF_HOST: device.host[0], CONF_TIMEOUT: broadlink.DEFAULT_TIMEOUT}
                    )
                    return await self.async_step_finish()

                if device.mac == self.device.mac:
                    await self.async_set_device(device, raise_on_progress=False)
                    return await self.async_step_finish()

                errors["base"] = "invalid_host"

            if self.source == config_entries.SOURCE_IMPORT:
                return self.async_abort(reason=errors["base"])

        data_schema = {
            vol.Required(CONF_HOST): str
        }
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(data_schema),
            errors=errors,
        )
    
    async def async_step_finish(self, user_input=None):
        """Choose a name for the device and create config entry."""
        device = self.device
        errors = {}

        # Abort reauthentication flow.
        self._abort_if_unique_id_configured(
            updates={CONF_HOST: device.host[0], CONF_TIMEOUT: device.timeout}
        )

        if user_input is not None:
            return self.async_create_entry(
                title=user_input[CONF_NAME],
                data={
                    CONF_NAME: device.name,
                    CONF_HOST: device.host[0],
                    CONF_MAC: device.mac.hex(),
                    CONF_TIMEOUT: device.timeout,
                    ATTR_MIN_TEMP: user_input[ATTR_MIN_TEMP],
                    ATTR_MAX_TEMP: user_input[ATTR_MAX_TEMP]
                },
            )

        data_schema = {
            vol.Required(CONF_NAME, default=device.name): str,
            vol.Optional(ATTR_MIN_TEMP, default=DEFAULT_MIN): cv.positive_int,
            vol.Optional(ATTR_MAX_TEMP, default=DEFAULT_MAX): cv.positive_int
        }

        return self.async_show_form(
            step_id="finish", data_schema=vol.Schema(data_schema), errors=errors
        )