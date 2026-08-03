"""Sensor platform for iXmanager integration."""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.components.sensor import SensorEntity
from homeassistant.components.sensor import SensorEntityDescription
from homeassistant.components.sensor import SensorStateClass
from homeassistant.const import PERCENTAGE
from homeassistant.const import EntityCategory
from homeassistant.const import UnitOfElectricCurrent
from homeassistant.const import UnitOfEnergy
from homeassistant.const import UnitOfPower
from homeassistant.const import UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.typing import StateType

from .const import CHARGING_STATUS_OPTIONS
from .const import PROPERTY_BOOST_REMAINING
from .const import PROPERTY_BSSID
from .const import PROPERTY_CHARGING_CURRENT
from .const import PROPERTY_CHARGING_CURRENT_L2
from .const import PROPERTY_CHARGING_CURRENT_L3
from .const import PROPERTY_CHARGING_STATUS
from .const import PROPERTY_CURRENT_CHARGING_POWER
from .const import PROPERTY_SIGNAL
from .const import PROPERTY_SSID
from .const import PROPERTY_TOTAL_ENERGY
from .coordinator import IXManagerConfigEntry
from .entity import IXManagerEntity
from .entity import IXManagerEntityDescription

_LOGGER = logging.getLogger(__name__)

PARALLEL_UPDATES = 0


def _percentage(value: Any) -> int:
    """Convert a signal reading to a percentage.

    Args:
        value: Raw value from the API

    Returns:
        Value clamped to the 0-100 range
    """
    return max(0, min(100, int(value)))


def _charging_status(value: Any) -> str | None:
    """Validate a charging status against the known SAE J1772 states.

    An enum sensor may only report values listed in its options, so anything
    unexpected is reported as unknown instead.

    Args:
        value: Raw value from the API

    Returns:
        The status, or None if the wallbox reported an unknown one
    """
    status = str(value)
    if status not in CHARGING_STATUS_OPTIONS:
        _LOGGER.warning("Wallbox reported an unknown charging status: %s", status)
        return None
    return status


@dataclass(frozen=True, kw_only=True)
class IXManagerSensorEntityDescription(
    IXManagerEntityDescription, SensorEntityDescription
):
    """Describes an iXmanager sensor."""

    value_fn: Callable[[Any], StateType] = lambda value: value


SENSORS: tuple[IXManagerSensorEntityDescription, ...] = (
    IXManagerSensorEntityDescription(
        key=PROPERTY_CURRENT_CHARGING_POWER,
        property_key=PROPERTY_CURRENT_CHARGING_POWER,
        translation_key="current_charging_power",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPower.WATT,
        value_fn=int,
    ),
    IXManagerSensorEntityDescription(
        key=PROPERTY_CHARGING_CURRENT,
        property_key=PROPERTY_CHARGING_CURRENT,
        translation_key="charging_current_l1",
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        suggested_display_precision=2,
        value_fn=float,
    ),
    IXManagerSensorEntityDescription(
        key=PROPERTY_CHARGING_CURRENT_L2,
        property_key=PROPERTY_CHARGING_CURRENT_L2,
        translation_key="charging_current_l2",
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        suggested_display_precision=2,
        value_fn=float,
    ),
    IXManagerSensorEntityDescription(
        key=PROPERTY_CHARGING_CURRENT_L3,
        property_key=PROPERTY_CHARGING_CURRENT_L3,
        translation_key="charging_current_l3",
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        suggested_display_precision=2,
        value_fn=float,
    ),
    IXManagerSensorEntityDescription(
        key=PROPERTY_TOTAL_ENERGY,
        property_key=PROPERTY_TOTAL_ENERGY,
        translation_key="total_energy",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
        suggested_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        suggested_display_precision=2,
        value_fn=int,
    ),
    IXManagerSensorEntityDescription(
        key=PROPERTY_BOOST_REMAINING,
        property_key=PROPERTY_BOOST_REMAINING,
        translation_key="boost_remaining",
        device_class=SensorDeviceClass.DURATION,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTime.SECONDS,
        value_fn=int,
    ),
    IXManagerSensorEntityDescription(
        key=PROPERTY_SIGNAL,
        property_key=PROPERTY_SIGNAL,
        translation_key="wifi_signal_strength",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=PERCENTAGE,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=_percentage,
    ),
    IXManagerSensorEntityDescription(
        key=PROPERTY_CHARGING_STATUS,
        property_key=PROPERTY_CHARGING_STATUS,
        translation_key="charging_status",
        device_class=SensorDeviceClass.ENUM,
        options=CHARGING_STATUS_OPTIONS,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=_charging_status,
    ),
    IXManagerSensorEntityDescription(
        key=PROPERTY_SSID,
        property_key=PROPERTY_SSID,
        translation_key="wifi_ssid",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=str,
    ),
    IXManagerSensorEntityDescription(
        key=PROPERTY_BSSID,
        property_key=PROPERTY_BSSID,
        translation_key="wifi_bssid",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        value_fn=str,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: IXManagerConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up iXmanager sensor entities.

    Args:
        hass: Home Assistant instance
        entry: Config entry
        async_add_entities: Callback to add entities
    """
    coordinator = entry.runtime_data

    async_add_entities(
        IXManagerSensor(coordinator, entry, description) for description in SENSORS
    )


class IXManagerSensor(IXManagerEntity, SensorEntity):
    """Sensor reporting a single iXmanager property."""

    entity_description: IXManagerSensorEntityDescription

    @property
    def native_value(self) -> StateType:
        """Return the state of the sensor.

        Returns:
            Converted sensor value, or None if missing or unparsable
        """
        value = self._property_value
        if value is None:
            return None

        try:
            return self.entity_description.value_fn(value)
        except (ValueError, TypeError):
            _LOGGER.warning(
                "Invalid value for %s: %s", self.entity_description.key, value
            )
            return None
