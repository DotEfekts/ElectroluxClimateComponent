"""Constants for the Electrolux Climate integration."""

from datetime import timedelta
from homeassistant.const import Platform

DOMAIN = "electrolux_climate"

FAN_QUIET = "quiet"
FAN_TURBO = "turbo"

MIN_TEMP = 17
MAX_TEMP = 30

PLATFORMS: list[Platform] = [Platform.CLIMATE]
SCAN_INTERVAL = timedelta(seconds=5)