"""Data update coordinator for iXmanager integration."""

import logging
from typing import Any, override

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api_client import IXManagerApiClient
from .const import DOMAIN, PROPERTIES_TO_FETCH, UPDATE_INTERVAL
from .exceptions import IXManagerAuthenticationError, IXManagerError

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
    """Class to manage fetching data from the iXmanager API."""

    config_entry: IXManagerConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        entry: IXManagerConfigEntry,
        api_client: IXManagerApiClient,
    ) -> None:
        """Initialize the coordinator.

        Args:
            hass: Home Assistant instance
            entry: Config entry owning this coordinator
            api_client: API client instance
        """
        self.api_client = api_client
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=UPDATE_INTERVAL,
        )

    @override
    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch every tracked property and flatten the response.

        The API returns each property either as a bare value or wrapped in
        ``{"value": X}``. Unwrapping happens here so that entities — and the
        optimistic writes that poke values straight into ``self.data`` — only
        ever deal with plain values.

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

        properties = {key: _unwrap(value) for key, value in data.items()}
        _LOGGER.debug("Coordinator updated data: %s", properties)
        return properties
