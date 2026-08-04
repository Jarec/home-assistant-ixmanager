"""The iXmanager integration."""

import logging

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady

from .api_client import IXManagerApiClient
from .const import CONF_API_KEY, CONF_SERIAL_NUMBER, PLATFORMS
from .coordinator import IXManagerConfigEntry, IXManagerDataUpdateCoordinator
from .exceptions import (
    IXManagerAuthenticationError,
    IXManagerConnectionError,
    IXManagerError,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: IXManagerConfigEntry) -> bool:
    """Set up iXmanager from a config entry.

    Args:
        hass: Home Assistant instance
        entry: Config entry to set up

    Returns:
        True if setup was successful

    Raises:
        ConfigEntryAuthFailed: If the API key was rejected
        ConfigEntryNotReady: If setup fails due to connection issues
    """
    api_client = IXManagerApiClient(
        hass, entry.data[CONF_API_KEY], entry.data[CONF_SERIAL_NUMBER]
    )

    try:
        await api_client.async_validate_connection()
    except IXManagerAuthenticationError as err:
        raise ConfigEntryAuthFailed(f"Authentication failed: {err}") from err
    except IXManagerConnectionError as err:
        raise ConfigEntryNotReady("Unable to connect to iXmanager API") from err
    except IXManagerError as err:
        raise ConfigEntryNotReady(f"Unexpected API response: {err}") from err

    coordinator = IXManagerDataUpdateCoordinator(hass, entry, api_client)

    # Fetch initial data so we have data when entities subscribe
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: IXManagerConfigEntry) -> bool:
    """Unload a config entry.

    Args:
        hass: Home Assistant instance
        entry: Config entry to unload

    Returns:
        True if unload was successful
    """
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_reload_entry(hass: HomeAssistant, entry: IXManagerConfigEntry) -> None:
    """Reload the config entry after its options changed.

    Registered as an update listener so that changing the cable type takes
    effect immediately instead of on the next Home Assistant restart.

    Args:
        hass: Home Assistant instance
        entry: Config entry to reload
    """
    await hass.config_entries.async_reload(entry.entry_id)
