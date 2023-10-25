import struct
import broadlink.exceptions as e
import typing as t

from broadlink.device import Device
from broadlink.exceptions import DataValidationError

from enum import IntEnum

MAX_TEMP = 40
MIN_TEMP = 0
DEVICE_TYPE = 0x4f9b

def create_from_device(device: Device):
    return electrolux(device.host, device.mac, device.devtype, device.timeout, device.name, "", "Electrolux", device.is_locked)

class electrolux(Device):
    """Controls an electrolux air conditioner.
    """

    TYPE = "ELECTROLUX_OEM"

    def __init__(self, host: t.Tuple[str, int], mac: t.Union[bytes, str], devtype: int, timeout: int = ..., name: str = "", model: str = "", manufacturer: str = "", is_locked: bool = False) -> None:
        super().__init__(host, mac, devtype, timeout, name, model, manufacturer, is_locked)
        self.auth()

    def _send(self, command: int, data: bytes = b"") -> bytes:
        """Send a packet to the device."""
        packet = bytearray(0xD)
        packet[0x00:0x02] = command.to_bytes(2, "little")
        packet[0x02:0x06] = bytes.fromhex("a5a55a5a")

        packet[0x08] = 0x01 if len(data) <= 2 else 0x02
        packet[0x09] = 0x0b
        packet[0xA:0xB] = len(data).to_bytes(2, "little")

        packet.extend(data)

        d_checksum = sum(packet[0x08:], 0xC0AD) & 0xFFFF
        packet[0x06:0x08] = d_checksum.to_bytes(2, "little")

        #print(' '.join(format(x, '02x') for x in packet))

        resp = self.send_packet(0x6A, packet)
        e.check_error(resp[0x22:0x24])
        dcry = self.decrypt(resp[0x38:])

        r_checksum = sum(dcry[0x08:], 0xC0AD) & 0xFFFF
        r_response = struct.unpack("h", dcry[0x06:0x08])[0]

        if r_checksum != r_response:
            raise e.BroadlinkException(DataValidationError, "Failed to validate JSON checksum.")

        r_length = struct.unpack("h", dcry[0xA:0xC])[0]

        payload = dcry[0xE:0xE + r_length]

        return payload

    def get_status(self) -> str:
        resp = self._send(0x0e, bytearray('{}', "ascii"))
        return str(resp, "ascii")

    def set_temp(self, temp: int) -> str:
        temp = max(MIN_TEMP, min(temp, MAX_TEMP))
        resp = self._send(0x17, bytearray('{"temp":%s}'%(temp), "ascii"))
        return str(resp, "ascii")

    def set_power(self, power_on: bool) -> str:
        resp = self._send(0x18, bytearray('{"ac_pwr":%s}'%(1 if power_on else 0), "ascii"))
        return str(resp, "ascii")
    
    class mode(IntEnum):
        AUTO = 4,
        COOL = 0,
        HEAT = 1,
        DRY = 2,
        FAN = 3,
        HEAT_8 = 6

    def set_mode(self, mode: mode) -> str:
        resp = self._send(0x19, bytearray('{"ac_mode":%s}'%(mode.value), "ascii"))
        return str(resp, "ascii")
    
    class fan(IntEnum):
        AUTO = 0,
        LOW = 1,
        MID = 2,
        HIGH = 3,
        TURBO = 4,
        QUIET = 5

    def set_fan(self, fan: fan) -> str:
        resp = self._send(0x19, bytearray('{"ac_mark":%s}'%(fan.value), "ascii"))
        return str(resp, "ascii")

    def set_swing(self, swing_on: bool) -> str:
        resp = self._send(0x19, bytearray('{"ac_vdir":%s}'%(1 if swing_on else 0), "ascii"))
        return str(resp, "ascii")

    def set_led(self, led_on: bool) -> str:
        resp = self._send(0x19, bytearray('{"scrdisp":%s}'%(1 if led_on else 0), "ascii"))
        return str(resp, "ascii")

    def set_sleep(self, sleep_on: bool) -> str:
        resp = self._send(0x18, bytearray('{"ac_slp":%s}'%(1 if sleep_on else 0), "ascii"))
        return str(resp, "ascii")

    def set_self_clean(self, clean_on: bool) -> str:
        resp = self._send(0x18, bytearray('{"mldprf":%s}'%(1 if clean_on else 0), "ascii"))
        return str(resp, "ascii")

    def set_timer(self, on_timer: bool, hours: int, minutes: int) -> str:

        hours = max(0, min(hours, 23))
        minutes = max(0, min(minutes, 59))

        resp = self._send(0x1f, bytearray('{"timer":"%02d%02d|0%s"}'%(hours,minutes,1 if on_timer else 0), "ascii"))
        return str(resp, "ascii")

    def clear_timer(self, on_timer: bool) -> str:
        resp = self.set_timer(on_timer, 0, 0)
        return resp