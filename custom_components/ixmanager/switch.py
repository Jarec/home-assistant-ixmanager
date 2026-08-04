"""Switch platform for iXmanager integration."""

from dataclasses import dataclass
from typing import Any, override

from homeassistant.components.switch import SwitchEntity, SwitchEntityDescription
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import PROPERTY_CHARGING_ENABLE, PROPERTY_SINGLE_PHASE
from .coordinator import IXManagerConfigEntry
from .entity import IXManagerEntity, IXManagerEntityDescription
from .util import coerce_bool

# Writes are serialized rather than dropped, so the last requested value wins
PARALLEL_UPDATES = 1


@dataclass(frozen=True, kw_only=True)
class IXManagerSwitchEntityDescription(
    IXManagerEntityDescription, SwitchEntityDescription
):
    """Describes an iXmanager switch."""


SWITCHES: tuple[IXManagerSwitchEntityDescription, ...] = (
    IXManagerSwitchEntityDescription(
        key="charging_enable",
        property_key=PROPERTY_CHARGING_ENABLE,
        translation_key="charging_enable",
    ),
    IXManagerSwitchEntityDescription(
        key="single_phase",
        property_key=PROPERTY_SINGLE_PHASE,
        translation_key="single_phase",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: IXManagerConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up iXmanager switch entities.

    Args:
        hass: Home Assistant instance
        entry: Config entry
        async_add_entities: Callback to add entities
    """
    coordinator = entry.runtime_data

    async_add_entities(
        IXManagerSwitch(coordinator, entry, description) for description in SWITCHES
    )


class IXManagerSwitch(IXManagerEntity, SwitchEntity):
    """Switch toggling a single boolean iXmanager property.

    No ``assumed_state``: the property can be read back, and the coordinator's
    pending-write overlay keeps the optimistic value stable until the device
    confirms it, so the state shown is a real one.
    """

    entity_description: IXManagerSwitchEntityDescription

    @property
    @override
    def is_on(self) -> bool | None:
        """Return true if the switch is on.

        Returns:
            Switch state, or None if not reported or not interpretable
        """
        value = self._property_value
        if value is None:
            return None

        state = coerce_bool(value)
        if state is None:
            self._warn_once(
                value,
                "Unrecognized boolean value for %s: %s",
                self.entity_description.key,
                value,
            )
        return state

    @override
    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the switch on.

        Args:
            **kwargs: Additional arguments

        Raises:
            HomeAssistantError: If the API rejected the write
        """
        await self._async_write_property(True)

    @override
    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the switch off.

        Args:
            **kwargs: Additional arguments

        Raises:
            HomeAssistantError: If the API rejected the write
        """
        await self._async_write_property(False)
