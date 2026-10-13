import struct
import broadlink.exceptions as e

from broadlink.device import Device
from broadlink.exceptions import DataValidationError

from enum import IntEnum

MAX_TEMP = 40
MIN_TEMP = 0
DEVICE_TYPE = 0x4F9B


def create_from_device(device: Device):
    """Create an internal electrolux object from a broadlink library device object."""
    return electrolux(
        device.host,
        device.mac,
        device.devtype,
        device.timeout,
        device.name,
        "",
        "Electrolux",
        device.is_locked,
    )


class electrolux(Device):
    """Controls an electrolux air conditioner."""

    TYPE = "ELECTROLUX_OEM"

    def __init__(
        self,
        host: tuple[str, int],
        mac: bytes | str,
        devtype: int,
        timeout: int = ...,
        name: str = "",
        model: str = "",
        manufacturer: str = "",
        is_locked: bool = False,
    ) -> None:
        """Entity constructor."""
        super().__init__(
            host, mac, devtype, timeout, name, model, manufacturer, is_locked
        )

    async def _send(self, command: int, data: bytes = b"") -> bytes:
        """Send a packet to the device."""
        packet = bytearray(0xD)
        packet[0x00:0x02] = command.to_bytes(2, "little")
        packet[0x02:0x06] = bytes.fromhex("a5a55a5a")

        packet[0x08] = 0x01 if len(data) <= 2 else 0x02
        packet[0x09] = 0x0B
        packet[0xA:0xB] = len(data).to_bytes(2, "little")

        packet.extend(data)

        d_checksum = sum(packet[0x08:], 0xC0AD) & 0xFFFF
        packet[0x06:0x08] = d_checksum.to_bytes(2, "little")

        # print(' '.join(format(x, '02x') for x in packet))

        resp = await self.send_packet(0x6A, packet)
        e.check_error(resp[0x22:0x24])
        dcry = self.decrypt(resp[0x38:])

        r_checksum = sum(dcry[0x08:], 0xC0AD) & 0xFFFF
        r_response = struct.unpack("<H", dcry[0x06:0x08])[0]

        if r_checksum != r_response:
            raise e.BroadlinkException(
                DataValidationError, "Failed to validate JSON checksum."
            )

        r_length = struct.unpack("<H", dcry[0xA:0xC])[0]

        return dcry[0xE : 0xE + r_length]

    async def get_status(self) -> str:
        """Retrieve the device status."""
        resp = await self._send(0x0E, bytearray("{}", "ascii"))
        return str(resp, "ascii")

    async def set_temp(self, temp: int) -> str:
        """Set the target temperature."""
        temp = max(MIN_TEMP, min(temp, MAX_TEMP))
        resp = await self._send(0x17, bytearray('{"temp":%s}' % (temp), "ascii"))
        return str(resp, "ascii")

    async def set_power(self, power_on: bool) -> str:
        """Turn the device on or off."""
        resp = await self._send(
            0x18, bytearray('{"ac_pwr":%s}' % (1 if power_on else 0), "ascii")
        )
        return str(resp, "ascii")

    class mode(IntEnum):
        """Definition for device modes."""

        AUTO = (4,)
        COOL = (0,)
        HEAT = (1,)
        DRY = (2,)
        FAN = (3,)
        HEAT_8 = 6

    async def set_mode(self, mode: mode) -> str:
        """Set the current device mode."""
        resp = await self._send(
            0x19, bytearray('{"ac_mode":%s}' % (mode.value), "ascii")
        )
        return str(resp, "ascii")

    class fan(IntEnum):
        """Definition for device fan speeds."""

        AUTO = (0,)
        LOW = (1,)
        MID = (2,)
        HIGH = (3,)
        TURBO = (4,)
        QUIET = 5

    async def set_fan(self, fan: fan) -> str:
        """Set the current device fan speed."""
        resp = await self._send(
            0x19, bytearray('{"ac_mark":%s}' % (fan.value), "ascii")
        )
        return str(resp, "ascii")

    async def set_swing(self, swing_on: bool) -> str:
        """Turn the device fan swing on or off."""
        resp = await self._send(
            0x19, bytearray('{"ac_vdir":%s}' % (1 if swing_on else 0), "ascii")
        )
        return str(resp, "ascii")

    async def set_led(self, led_on: bool) -> str:
        """Turn the device LED on or off."""
        resp = await self._send(
            0x19, bytearray('{"scrdisp":%s}' % (1 if led_on else 0), "ascii")
        )
        return str(resp, "ascii")

    async def set_sleep(self, sleep_on: bool) -> str:
        """Turn sleep mode on the device on or off."""
        resp = await self._send(
            0x18, bytearray('{"ac_slp":%s}' % (1 if sleep_on else 0), "ascii")
        )
        return str(resp, "ascii")

    async def set_self_clean(self, clean_on: bool) -> str:
        """Turn the device self clean mode on or off."""
        resp = await self._send(
            0x18, bytearray('{"mldprf":%s}' % (1 if clean_on else 0), "ascii")
        )
        return str(resp, "ascii")

    async def set_timer(self, on_timer: bool, hours: int, minutes: int) -> str:
        """Set the device sleep/wake timer."""
        hours = max(0, min(hours, 23))
        minutes = max(0, min(minutes, 59))

        resp = await self._send(
            0x1F,
            bytearray(
                '{"timer":"%02d%02d|0%s"}' % (hours, minutes, 1 if on_timer else 0),
                "ascii",
            ),
        )
        return str(resp, "ascii")

    async def clear_timer(self, on_timer: bool) -> str:
        """Clear the current sleep/wake timer."""
        return await self.set_timer(on_timer, 0, 0)
