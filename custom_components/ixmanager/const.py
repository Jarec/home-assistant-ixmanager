"""Constants for the iXmanager integration."""

from __future__ import annotations

from datetime import timedelta
from typing import Final

from homeassistant.const import Platform

# Domain
DOMAIN: Final = "ixmanager"

# API Configuration
BASE_URL: Final = "https://evcharger.ixcommand.com/api/v1"
API_TIMEOUT: Final = 10
UPDATE_INTERVAL: Final = timedelta(seconds=30)

# Seconds to wait after a write before re-reading the device to verify it
WRITE_VERIFY_DELAY: Final = 2

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

# Vehicle charging states reported by the wallbox, following SAE J1772
CHARGING_STATUS_OPTIONS: Final = [
    "INIT",
    "IDLE",
    "CONNECTED",
    "CHARGING",
    "CHARGING_WITH_VENTILATION",
    "CONTROL_PILOT_ERROR",
    "ERROR",
]

# Cable types and specifications
CABLE_TYPE_16A: Final = "16A"
CABLE_TYPE_32A: Final = "32A"

CABLE_TYPES: Final = {
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
