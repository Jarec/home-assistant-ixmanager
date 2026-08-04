"""Constants for the iXmanager integration."""

from datetime import timedelta
from typing import Final, TypedDict

from homeassistant.const import Platform

# Domain
DOMAIN: Final = "ixmanager"

# API Configuration
BASE_URL: Final = "https://evcharger.ixcommand.com/api/v1"
API_TIMEOUT: Final = 10
UPDATE_INTERVAL: Final = timedelta(seconds=15)

# Cooldown of the debouncer that re-reads the device after a write, in seconds.
# Several writes in a row therefore collapse into a single verification refresh.
WRITE_VERIFY_DELAY: Final = 2

# How long an optimistic value is held before the device is considered to have
# rejected it, in seconds. Tuned against UPDATE_INTERVAL: with the verification
# refresh above, a write is checked at roughly +2s and again at +17s, so this
# gives the cloud two chances to catch up before the write is given up on.
PENDING_WRITE_TIMEOUT: Final = 15

# Configuration keys
CONF_API_KEY: Final = "api_key"
CONF_SERIAL_NUMBER: Final = "serial_number"
CONF_CABLE_TYPE: Final = "cable_type"

# Device properties
PROPERTY_CHARGING_ENABLE: Final = "chargingEnable"
PROPERTY_MAXIMUM_CURRENT: Final = "maximumCurrent"
PROPERTY_CURRENT_CHARGING_POWER: Final = "currentChargingPower"
PROPERTY_TOTAL_ENERGY: Final = "totalEnergy"
PROPERTY_SINGLE_PHASE: Final = "singlePhase"
PROPERTY_SIGNAL: Final = "signal"
PROPERTY_CHARGING_STATUS: Final = "chargingStatus"
PROPERTY_TARGET_CURRENT: Final = "targetCurrent"
PROPERTY_CHARGING_CURRENT: Final = "chargingCurrent"
PROPERTY_CHARGING_CURRENT_L2: Final = "chargingCurrentL2"
PROPERTY_CHARGING_CURRENT_L3: Final = "chargingCurrentL3"
PROPERTY_CHARGING_STATE: Final = "chargingState"
PROPERTY_BOOST_CURRENT: Final = "boostCurrent"
PROPERTY_BOOST_TIME: Final = "boostTime"
PROPERTY_BOOST_REMAINING: Final = "boostRemaining"
PROPERTY_BOOST_STATE: Final = "boostState"
PROPERTY_SSID: Final = "ssid"
PROPERTY_BSSID: Final = "bssid"

# Every property fetched on each coordinator update
PROPERTIES_TO_FETCH: Final = [
    PROPERTY_CHARGING_ENABLE,
    PROPERTY_MAXIMUM_CURRENT,
    PROPERTY_TARGET_CURRENT,
    PROPERTY_CURRENT_CHARGING_POWER,
    PROPERTY_CHARGING_CURRENT,
    PROPERTY_CHARGING_CURRENT_L2,
    PROPERTY_CHARGING_CURRENT_L3,
    PROPERTY_TOTAL_ENERGY,
    PROPERTY_SINGLE_PHASE,
    PROPERTY_SIGNAL,
    PROPERTY_CHARGING_STATUS,
    PROPERTY_CHARGING_STATE,
    PROPERTY_BOOST_CURRENT,
    PROPERTY_BOOST_TIME,
    PROPERTY_BOOST_REMAINING,
    PROPERTY_BOOST_STATE,
    PROPERTY_SSID,
    PROPERTY_BSSID,
]

# Vehicle charging states reported by the wallbox, following SAE J1772.
# The API reports these in upper case; they are lower-cased on the way in
# because a translation key may only contain [a-z0-9-_].
CHARGING_STATUS_OPTIONS: Final = [
    "init",
    "idle",
    "connected",
    "charging",
    "charging_with_ventilation",
    "control_pilot_error",
    "error",
]

# Cable types and specifications
CABLE_TYPE_16A: Final = "16a"
CABLE_TYPE_32A: Final = "32a"


class CableSpec(TypedDict):
    """Specification of a supported charging cable.

    Attributes:
        name: Human readable cable name, used in the config entry title
        max_current: Highest current the cable may carry, in ampere
        description: Longer explanation of the cable type
    """

    name: str
    max_current: int
    description: str


CABLE_TYPES: Final[dict[str, CableSpec]] = {
    CABLE_TYPE_16A: {
        "name": "Type 2 Cable (16A Max)",
        "max_current": 16,
        "description": "Standard charging cable, maximum 16A",
    },
    CABLE_TYPE_32A: {
        "name": "Type 2 Cable (32A Max)",
        "max_current": 32,
        "description": "High power charging cable, maximum 32A",
    },
}

# Charging current limits
MIN_CHARGING_CURRENT: Final = 6
CHARGING_CURRENT_STEP: Final = 1

# Boost duration limits, in seconds (the API accepts 0 to 24 hours)
BOOST_TIME_MIN: Final = 0
BOOST_TIME_MAX: Final = 86400
BOOST_TIME_STEP: Final = 60

# Default values
DEFAULT_NAME: Final = "iXmanager"
DEFAULT_CABLE_TYPE: Final = CABLE_TYPE_16A

# Platforms
PLATFORMS: Final = [
    Platform.BINARY_SENSOR,
    Platform.NUMBER,
    Platform.SENSOR,
    Platform.SWITCH,
]
