"""Shared entity base for the iXmanager integration."""

import asyncio
from dataclasses import dataclass
import logging
from typing import Any, override

from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import EntityDescription
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_SERIAL_NUMBER, DOMAIN, WRITE_VERIFY_DELAY
from .coordinator import IXManagerConfigEntry, IXManagerDataUpdateCoordinator
from .exceptions import IXManagerError

_LOGGER = logging.getLogger(__name__)


def coerce_bool(value: Any) -> bool:
    """Interpret an API property value as a boolean.

    The API reports booleans natively, but may fall back to their string form.

    Args:
        value: Raw value from the API

    Returns:
        True if the value represents a truthy property
    """
    if isinstance(value, bool):
        return value
    return str(value).lower() == "true"


@dataclass(frozen=True, kw_only=True)
class IXManagerEntityDescription(EntityDescription):
    """Entity description carrying the iXmanager API property key.

    ``key`` is the unique ID suffix and must never change for an existing
    entity. ``property_key`` is the key used against the API. For sensors the
    two are identical (camelCase), for writable platforms they differ
    (``charging_enable`` vs. ``chargingEnable``).
    """

    property_key: str


class IXManagerEntity(CoordinatorEntity[IXManagerDataUpdateCoordinator]):
    """Base entity binding one API property to one Home Assistant entity."""

    entity_description: IXManagerEntityDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: IXManagerDataUpdateCoordinator,
        entry: IXManagerConfigEntry,
        description: IXManagerEntityDescription,
    ) -> None:
        """Initialize the entity.

        Args:
            coordinator: Data update coordinator
            entry: Config entry the entity belongs to
            description: Description of this entity
        """
        super().__init__(coordinator)
        self.entity_description = description
        self._property_key = description.property_key
        self._api_call_in_progress = False

        serial_number = entry.data[CONF_SERIAL_NUMBER]
        self._attr_unique_id = f"{serial_number}_{description.key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, serial_number)},
            name=f"iXmanager {serial_number}",
            manufacturer="R-EVC",
            model="Wallbox EcoVolter",
            serial_number=serial_number,
        )

    @property
    @override
    def available(self) -> bool:
        """Return if entity is available.

        Returns:
            True if the coordinator holds a usable value for this property
        """
        return (
            self.coordinator.last_update_success
            and self.coordinator.data is not None
            and self.coordinator.data.get(self._property_key) is not None
        )

    @property
    def _property_value(self) -> Any:
        """Return the raw value of this entity's property.

        Returns:
            The value from the coordinator, or None if unavailable
        """
        if not self.available:
            return None
        return self.coordinator.data.get(self._property_key)

    async def _async_write_property(self, value: Any) -> None:
        """Write a property optimistically and verify it afterwards.

        The value is pushed into the coordinator data and rendered immediately
        so the UI stays responsive, then sent to the API. A background task
        re-reads the device shortly after to correct the state if the wallbox
        disagreed.

        Args:
            value: Value to send to the API

        Raises:
            HomeAssistantError: If the API rejected the write
        """
        if self._api_call_in_progress:
            _LOGGER.debug(
                "API call already in progress for %s, ignoring request",
                self._property_key,
            )
            return

        self._api_call_in_progress = True
        try:
            _LOGGER.debug("Setting %s to %s", self._property_key, value)

            if self.coordinator.data is not None:
                self.coordinator.data[self._property_key] = value
                self.async_write_ha_state()

            await self.coordinator.api_client.async_set_property(
                self._property_key, value
            )

        except IXManagerError as err:
            _LOGGER.error("Failed to set %s to %s: %s", self._property_key, value, err)
            await self.coordinator.async_refresh()
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="write_failed",
                translation_placeholders={
                    "property_key": self._property_key,
                    "value": str(value),
                    "error": str(err),
                },
            ) from err

        finally:
            self._api_call_in_progress = False

        self.hass.async_create_background_task(
            self._async_verify_write(),
            name=f"{DOMAIN} verify {self._attr_unique_id}",
        )

    async def _async_verify_write(self) -> None:
        """Re-read the device after a write to reconcile the optimistic state.

        ``async_refresh`` is used rather than ``async_request_refresh`` because
        the latter is debounced by ten seconds, which would make the delay
        below meaningless.
        """
        await asyncio.sleep(WRITE_VERIFY_DELAY)
        try:
            await self.coordinator.async_refresh()
        except Exception as err:  # noqa: BLE001 - background task, must never escape
            _LOGGER.debug("Write verification refresh failed: %s", err)
