"""Data update coordinator for iXmanager integration."""

import logging
from typing import Any, override

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.debounce import Debouncer
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api_client import IXManagerApiClient
from .const import (
    DOMAIN,
    PENDING_WRITE_TIMEOUT,
    PROPERTIES_TO_FETCH,
    UPDATE_INTERVAL,
    WRITE_VERIFY_DELAY,
)
from .exceptions import IXManagerAuthenticationError, IXManagerError
from .util import WritableValue, values_match

_LOGGER = logging.getLogger(__name__)

type IXManagerConfigEntry = ConfigEntry[IXManagerDataUpdateCoordinator]


def _unwrap(value: Any) -> Any:
    """Unwrap a property the API returned as ``{"value": X}``.

    Args:
        value: Raw property value from the API, either wrapped or bare

    Returns:
        The plain value
    """
    if isinstance(value, dict) and "value" in value:
        return value["value"]
    return value


class IXManagerDataUpdateCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Class to manage fetching data from the iXmanager API.

    Besides polling, the coordinator owns the pending-write overlay: a value
    written by an entity is rendered immediately and kept in place until the
    device confirms it or the write times out. That is what lets the entities
    respond instantly without the state flapping back and forth while the
    cloud catches up.
    """

    config_entry: IXManagerConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        entry: IXManagerConfigEntry,
        api_client: IXManagerApiClient,
    ) -> None:
        """Initialize the coordinator.

        The refresh debouncer is deliberately not the default one: with
        ``immediate=False`` it becomes a pure trailing debounce, so a burst of
        writes results in exactly one verification refresh WRITE_VERIFY_DELAY
        after the last of them.

        Args:
            hass: Home Assistant instance
            entry: Config entry owning this coordinator
            api_client: API client instance
        """
        self.api_client = api_client
        self._pending: dict[str, tuple[WritableValue, float]] = {}
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=UPDATE_INTERVAL,
            request_refresh_debouncer=Debouncer(
                hass, _LOGGER, cooldown=WRITE_VERIFY_DELAY, immediate=False
            ),
        )

    @property
    def pending_writes(self) -> dict[str, WritableValue]:
        """Return the values written but not yet confirmed by the device.

        Returns:
            Mapping of property key to the value awaiting confirmation
        """
        return {key: value for key, (value, _) in self._pending.items()}

    @callback
    def async_set_pending(self, key: str, value: WritableValue) -> None:
        """Render a written value immediately and hold it until confirmed.

        ``async_set_updated_data`` is used rather than a direct mutation of
        ``self.data`` so that every listener is notified — a value can bound
        another entity, as ``maximumCurrent`` does for the target current.

        Args:
            key: API property key being written
            value: Value sent to the API
        """
        self._pending[key] = (value, self.hass.loop.time() + PENDING_WRITE_TIMEOUT)
        self.async_set_updated_data({**(self.data or {}), key: value})

    @callback
    def async_clear_pending(self, key: str) -> None:
        """Drop a pending write, typically because the API rejected it.

        Args:
            key: API property key to stop holding
        """
        self._pending.pop(key, None)

    def _apply_pending(self, fetched: dict[str, Any]) -> dict[str, Any]:
        """Overlay values still awaiting confirmation onto freshly fetched data.

        A pending value survives until the device reports it back, at which
        point it is dropped as converged, or until its deadline passes, at
        which point the device is taken at its word and the disagreement is
        logged — otherwise a rejected command would silently revert.

        Args:
            fetched: Properties as reported by the API, modified in place

        Returns:
            The properties with unconfirmed writes applied
        """
        now = self.hass.loop.time()

        for key, (value, expires) in list(self._pending.items()):
            if values_match(value, fetched.get(key)):
                del self._pending[key]
            elif now > expires:
                del self._pending[key]
                _LOGGER.warning(
                    "Wallbox did not accept %s=%s, it reports %s",
                    key,
                    value,
                    fetched.get(key),
                )
            else:
                fetched[key] = value

        return fetched

    @override
    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch every tracked property, flatten it and re-apply pending writes.

        The API returns each property either as a bare value or wrapped in
        ``{"value": X}``. Unwrapping happens here so that entities only ever
        deal with plain values.

        Returns:
            Dictionary mapping each property key to its plain value

        Raises:
            ConfigEntryAuthFailed: If the API key was rejected, so that Home
                Assistant starts the reauth flow
            UpdateFailed: If the update fails for any other reason
        """
        try:
            data = await self.api_client.async_get_properties(PROPERTIES_TO_FETCH)

        except IXManagerAuthenticationError as err:
            raise ConfigEntryAuthFailed(f"Authentication failed: {err}") from err
        except IXManagerError as err:
            raise UpdateFailed(f"Error communicating with API: {err}") from err
        except Exception as err:
            _LOGGER.exception("Unexpected error fetching iXmanager data")
            raise UpdateFailed(f"Unexpected error: {err}") from err

        properties = self._apply_pending(
            {key: _unwrap(value) for key, value in data.items()}
        )
        _LOGGER.debug("Coordinator updated data: %s", properties)
        return properties
