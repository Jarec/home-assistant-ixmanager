"""Binary sensor platform for iXmanager integration."""

from dataclasses import dataclass
from typing import override

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import PROPERTY_BOOST_STATE, PROPERTY_CHARGING_STATE
from .coordinator import IXManagerConfigEntry
from .entity import IXManagerEntity, IXManagerEntityDescription, coerce_bool

PARALLEL_UPDATES = 0


@dataclass(frozen=True, kw_only=True)
class IXManagerBinarySensorEntityDescription(
    IXManagerEntityDescription, BinarySensorEntityDescription
):
    """Describes an iXmanager binary sensor."""


BINARY_SENSORS: tuple[IXManagerBinarySensorEntityDescription, ...] = (
    IXManagerBinarySensorEntityDescription(
        key="charging_state",
        property_key=PROPERTY_CHARGING_STATE,
        translation_key="charging_state",
        device_class=BinarySensorDeviceClass.BATTERY_CHARGING,
    ),
    IXManagerBinarySensorEntityDescription(
        key="boost_state",
        property_key=PROPERTY_BOOST_STATE,
        translation_key="boost_state",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: IXManagerConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up iXmanager binary sensor entities.

    Args:
        hass: Home Assistant instance
        entry: Config entry
        async_add_entities: Callback to add entities
    """
    coordinator = entry.runtime_data

    async_add_entities(
        IXManagerBinarySensor(coordinator, entry, description)
        for description in BINARY_SENSORS
    )


class IXManagerBinarySensor(IXManagerEntity, BinarySensorEntity):
    """Binary sensor reporting a single boolean iXmanager property."""

    entity_description: IXManagerBinarySensorEntityDescription

    @property
    @override
    def is_on(self) -> bool | None:
        """Return true if the property is set.

        Returns:
            Property state, or None if not available
        """
        value = self._property_value
        if value is None:
            return None
        return coerce_bool(value)
