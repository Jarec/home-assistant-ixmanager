"""API client for iXmanager integration."""

import asyncio
import logging
from typing import Any, NoReturn

import aiohttp
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import API_TIMEOUT, BASE_URL, PROPERTY_CHARGING_ENABLE
from .exceptions import (
    IXManagerAuthenticationError,
    IXManagerConnectionError,
    IXManagerError,
    IXManagerNotFoundError,
)
from .util import WritableValue

_LOGGER = logging.getLogger(__name__)


class IXManagerApiClient:
    """API client for iXmanager wallbox."""

    def __init__(self, hass: HomeAssistant, api_key: str, controller_id: str) -> None:
        """Initialize the API client.

        Args:
            hass: Home Assistant instance
            api_key: API key for authentication
            controller_id: Device serial number/controller ID
        """
        self._hass = hass
        self._api_key = api_key
        self._controller_id = controller_id
        self._session = async_get_clientsession(hass)

    @property
    def _url(self) -> str:
        """Return the properties endpoint for the configured controller.

        Returns:
            Fully qualified endpoint URL
        """
        return f"{BASE_URL}/thing/{self._controller_id}/properties"

    @staticmethod
    def _raise_for_status(status: int) -> NoReturn:
        """Translate an unsuccessful HTTP status into an integration exception.

        Args:
            status: HTTP status code returned by the API

        Raises:
            IXManagerAuthenticationError: If the API key was rejected
            IXManagerNotFoundError: If the controller or property is unknown
            IXManagerError: For any other unsuccessful status
        """
        if status in (401, 403):
            raise IXManagerAuthenticationError("Invalid API key")
        if status == 404:
            raise IXManagerNotFoundError("Controller or property not found")
        raise IXManagerError(f"API returned status {status}")

    async def async_get_properties(self, keys: list[str]) -> dict[str, Any]:
        """Get device properties from the API.

        Args:
            keys: List of property keys to retrieve

        Returns:
            Dictionary containing property data

        Raises:
            IXManagerConnectionError: If connection to API fails
            IXManagerAuthenticationError: If the API key was rejected
            IXManagerNotFoundError: If the controller is unknown
            IXManagerError: If API returns an error
        """
        headers = {"X-API-KEY": self._api_key}
        params = {"keys": keys}

        try:
            _LOGGER.debug("Fetching properties: %s", keys)
            async with (
                asyncio.timeout(API_TIMEOUT),
                self._session.get(
                    self._url, headers=headers, params=params
                ) as response,
            ):
                if response.status != 200:
                    self._raise_for_status(response.status)

                data: dict[str, Any] = await response.json()

        except TimeoutError as err:
            raise IXManagerConnectionError(
                "Timeout connecting to iXmanager API"
            ) from err
        except aiohttp.ClientError as err:
            raise IXManagerConnectionError(
                f"Error connecting to iXmanager API: {err}"
            ) from err

        _LOGGER.debug("Received data: %s", data)
        return data

    async def async_set_property(self, key: str, value: WritableValue) -> None:
        """Set a device property via the API.

        Args:
            key: Property key to set
            value: Value to set

        Raises:
            IXManagerConnectionError: If connection to API fails
            IXManagerAuthenticationError: If the API key was rejected
            IXManagerNotFoundError: If the controller or property is unknown
            IXManagerError: If API returns an error
        """
        headers = {"X-API-KEY": self._api_key, "Content-Type": "application/json"}
        data = {key: value}

        try:
            _LOGGER.debug("Setting property %s to %s", key, value)
            async with (
                asyncio.timeout(API_TIMEOUT),
                self._session.patch(self._url, headers=headers, json=data) as response,
            ):
                if response.status not in (200, 204):
                    self._raise_for_status(response.status)

                _LOGGER.debug("Successfully set property %s", key)

        except TimeoutError as err:
            raise IXManagerConnectionError(
                "Timeout connecting to iXmanager API"
            ) from err
        except aiohttp.ClientError as err:
            raise IXManagerConnectionError(
                f"Error connecting to iXmanager API: {err}"
            ) from err

    async def async_validate_connection(self) -> None:
        """Validate the API connection and credentials.

        Raises:
            IXManagerConnectionError: If connection fails
            IXManagerAuthenticationError: If the API key was rejected
            IXManagerNotFoundError: If the serial number is unknown
            IXManagerError: If API returns an error
        """
        await self.async_get_properties([PROPERTY_CHARGING_ENABLE])
