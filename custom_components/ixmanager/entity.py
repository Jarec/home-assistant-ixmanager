"""Shared entity base for the iXmanager integration."""

from dataclasses import dataclass
import logging
from typing import Any

from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import EntityDescription
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_SERIAL_NUMBER, DOMAIN
from .coordinator import IXManagerConfigEntry, IXManagerDataUpdateCoordinator
from .exceptions import IXManagerError
from .util import WritableValue

_LOGGER = logging.getLogger(__name__)


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
        self._warned_values: set[str] = set()

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
    def _property_value(self) -> Any:
        """Return the raw value of this entity's property.

        A property the API did not report yields None, which surfaces as
        ``unknown`` — not as ``unavailable``. Availability is inherited from
        ``CoordinatorEntity`` and answers a different question: whether the
        wallbox can be reached at all. Conflating the two would tear holes in
        the recorder history and fire availability automations whenever a
        single value went missing.

        Returns:
            The value from the coordinator, or None if it was not reported
        """
        return self.coordinator.data.get(self._property_key)

    def _warn_once(self, token: object, message: str, *args: object) -> None:
        """Log a warning only the first time a given value is seen.

        The coordinator polls continuously, so an unexpected value would
        otherwise be logged on every single update.

        Args:
            token: Value identifying this warning; repeats are suppressed
            message: Logging format string
            *args: Arguments for the format string
        """
        key = repr(token)
        if key in self._warned_values:
            return

        self._warned_values.add(key)
        _LOGGER.warning(message, *args)

    async def _async_write_property(self, value: WritableValue) -> None:
        """Write a property optimistically and have the device confirm it.

        The value is handed to the coordinator, which renders it immediately
        and holds it until the device reports it back, so the UI responds at
        once without flapping. The trailing refresh request is debounced, so a
        burst of writes costs a single verification read.

        Concurrent writes are serialized by ``PARALLEL_UPDATES`` on the
        platform rather than being dropped, so the last value a user asked for
        always reaches the device.

        Args:
            value: Value to send to the API

        Raises:
            HomeAssistantError: If the API rejected the write
        """
        _LOGGER.debug("Setting %s to %s", self._property_key, value)
        self.coordinator.async_set_pending(self._property_key, value)

        try:
            await self.coordinator.api_client.async_set_property(
                self._property_key, value
            )
        except IXManagerError as err:
            _LOGGER.error("Failed to set %s to %s: %s", self._property_key, value, err)
            # The write is known to have failed, so do not keep showing it.
            self.coordinator.async_clear_pending(self._property_key)
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

        await self.coordinator.async_request_refresh()
