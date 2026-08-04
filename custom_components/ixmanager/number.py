"""Number platform for iXmanager integration."""

from collections.abc import Callable
from dataclasses import dataclass
import logging
from typing import Any, override

from homeassistant.components.number import (
    DEFAULT_MAX_VALUE,
    DEFAULT_MIN_VALUE,
    NumberDeviceClass,
    NumberEntity,
    NumberEntityDescription,
    NumberMode,
)
from homeassistant.const import UnitOfElectricCurrent, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import (
    BOOST_TIME_MAX,
    BOOST_TIME_MIN,
    BOOST_TIME_STEP,
    CABLE_TYPES,
    CHARGING_CURRENT_STEP,
    CONF_CABLE_TYPE,
    DEFAULT_CABLE_TYPE,
    MIN_CHARGING_CURRENT,
    PROPERTY_BOOST_CURRENT,
    PROPERTY_BOOST_TIME,
    PROPERTY_MAXIMUM_CURRENT,
    PROPERTY_TARGET_CURRENT,
)
from .coordinator import IXManagerConfigEntry, IXManagerDataUpdateCoordinator
from .entity import IXManagerEntity, IXManagerEntityDescription

_LOGGER = logging.getLogger(__name__)

PARALLEL_UPDATES = 0


def _cable_max(cable_max: int, data: dict[str, Any]) -> float:
    """Cap a current at the configured cable rating.

    Args:
        cable_max: Maximum current the configured cable can carry
        data: Current coordinator data, unused

    Returns:
        The cable limit
    """
    return float(cable_max)


def _target_current_max(cable_max: int, data: dict[str, Any]) -> float:
    """Cap the target current at the wallbox's live maximum current setting.

    Args:
        cable_max: Maximum current the configured cable can carry
        data: Current coordinator data

    Returns:
        The lower of the cable limit and the maximum current setting
    """
    maximum_current = data.get(PROPERTY_MAXIMUM_CURRENT)
    if maximum_current is None:
        return float(cable_max)

    try:
        return min(float(cable_max), float(maximum_current))
    except ValueError, TypeError:
        _LOGGER.warning("Invalid maximum current value: %s", maximum_current)
        return float(cable_max)


@dataclass(frozen=True, kw_only=True)
class IXManagerNumberEntityDescription(
    IXManagerEntityDescription, NumberEntityDescription
):
    """Describes an iXmanager number entity.

    ``max_value_fn`` derives the upper bound from the configured cable and the
    live device data. Descriptions that set it must also set
    ``native_min_value``, which is used as the floor of the derived range.
    Descriptions without it fall back to their own ``native_max_value``.
    """

    max_value_fn: Callable[[int, dict[str, Any]], float] | None = None


NUMBERS: tuple[IXManagerNumberEntityDescription, ...] = (
    IXManagerNumberEntityDescription(
        key="maximum_current",
        property_key=PROPERTY_MAXIMUM_CURRENT,
        translation_key="maximum_current",
        device_class=NumberDeviceClass.CURRENT,
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        native_min_value=MIN_CHARGING_CURRENT,
        native_step=CHARGING_CURRENT_STEP,
        mode=NumberMode.SLIDER,
        max_value_fn=_cable_max,
    ),
    IXManagerNumberEntityDescription(
        key="target_current",
        property_key=PROPERTY_TARGET_CURRENT,
        translation_key="target_current",
        device_class=NumberDeviceClass.CURRENT,
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        native_min_value=MIN_CHARGING_CURRENT,
        native_step=CHARGING_CURRENT_STEP,
        mode=NumberMode.SLIDER,
        max_value_fn=_target_current_max,
    ),
    IXManagerNumberEntityDescription(
        key="boost_current",
        property_key=PROPERTY_BOOST_CURRENT,
        translation_key="boost_current",
        device_class=NumberDeviceClass.CURRENT,
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        native_min_value=MIN_CHARGING_CURRENT,
        native_step=CHARGING_CURRENT_STEP,
        mode=NumberMode.SLIDER,
        max_value_fn=_target_current_max,
    ),
    IXManagerNumberEntityDescription(
        key="boost_time",
        property_key=PROPERTY_BOOST_TIME,
        translation_key="boost_time",
        device_class=NumberDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.SECONDS,
        native_min_value=BOOST_TIME_MIN,
        native_max_value=BOOST_TIME_MAX,
        native_step=BOOST_TIME_STEP,
        mode=NumberMode.BOX,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: IXManagerConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up iXmanager number entities.

    Args:
        hass: Home Assistant instance
        entry: Config entry
        async_add_entities: Callback to add entities
    """
    coordinator = entry.runtime_data

    async_add_entities(
        IXManagerNumber(coordinator, entry, description) for description in NUMBERS
    )


class IXManagerNumber(IXManagerEntity, NumberEntity):
    """Number entity writing a single integer iXmanager property."""

    entity_description: IXManagerNumberEntityDescription

    def __init__(
        self,
        coordinator: IXManagerDataUpdateCoordinator,
        entry: IXManagerConfigEntry,
        description: IXManagerNumberEntityDescription,
    ) -> None:
        """Initialize the number entity.

        Args:
            coordinator: Data update coordinator
            entry: Config entry
            description: Description of this entity
        """
        super().__init__(coordinator, entry, description)
        cable_type = entry.data.get(CONF_CABLE_TYPE, DEFAULT_CABLE_TYPE)
        cable_spec = CABLE_TYPES.get(cable_type, CABLE_TYPES[DEFAULT_CABLE_TYPE])
        self._cable_max_current = cable_spec["max_current"]

    @property
    @override
    def native_max_value(self) -> float:
        """Return the highest value this entity currently accepts.

        Current limits derive their ceiling from the configured cable and the
        live device data through ``max_value_fn``; entities without one — such
        as the boost duration — use the fixed range from their description.
        Home Assistant validates any requested value against this before
        ``async_set_native_value`` is reached.

        Returns:
            Maximum settable value in the entity's native unit
        """
        native_max_value = self.entity_description.native_max_value
        max_value_fn = self.entity_description.max_value_fn
        if max_value_fn is None:
            if native_max_value is None:
                return DEFAULT_MAX_VALUE
            return native_max_value

        native_min_value = self.entity_description.native_min_value
        if native_min_value is None:
            native_min_value = DEFAULT_MIN_VALUE

        return max(
            native_min_value,
            max_value_fn(self._cable_max_current, self.coordinator.data or {}),
        )

    @property
    @override
    def native_value(self) -> float | None:
        """Return the current value.

        Returns:
            Current value, or None if missing or unparsable
        """
        value = self._property_value
        if value is None:
            return None

        try:
            return float(value)
        except ValueError, TypeError:
            _LOGGER.warning(
                "Invalid value for %s: %s", self.entity_description.key, value
            )
            return None

    @override
    async def async_set_native_value(self, value: float) -> None:
        """Write the value to the device.

        Args:
            value: Value to set, already validated against the min/max range

        Raises:
            HomeAssistantError: If the API rejected the write
        """
        await self._async_write_property(int(value))
