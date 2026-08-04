"""Diagnostics support for the iXmanager integration."""

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.core import HomeAssistant

from .const import CONF_API_KEY, CONF_SERIAL_NUMBER, PROPERTY_BSSID, PROPERTY_SSID
from .coordinator import IXManagerConfigEntry

TO_REDACT = {CONF_API_KEY, CONF_SERIAL_NUMBER, "unique_id"}

# Diagnostics get pasted into public issues, so the home network is hidden too
TO_REDACT_DATA = {PROPERTY_SSID, PROPERTY_BSSID}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: IXManagerConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry.

    Args:
        hass: Home Assistant instance
        entry: Config entry to describe

    Returns:
        Diagnostics payload with credentials and network details redacted
    """
    coordinator = entry.runtime_data

    return {
        "entry": async_redact_data(entry.as_dict(), TO_REDACT),
        "last_update_success": coordinator.last_update_success,
        "data": (
            async_redact_data(coordinator.data, TO_REDACT_DATA)
            if coordinator.data
            else coordinator.data
        ),
    }
