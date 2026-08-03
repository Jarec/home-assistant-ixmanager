"""Config flow for iXmanager integration."""

from __future__ import annotations

import logging
from collections.abc import Mapping
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry
from homeassistant.config_entries import ConfigFlow
from homeassistant.config_entries import ConfigFlowResult
from homeassistant.config_entries import OptionsFlow
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.core import callback
from homeassistant.helpers.selector import SelectSelector
from homeassistant.helpers.selector import SelectSelectorConfig
from homeassistant.helpers.selector import SelectSelectorMode

from .api_client import IXManagerApiClient
from .const import CABLE_TYPES
from .const import CONF_API_KEY
from .const import CONF_CABLE_TYPE
from .const import CONF_SERIAL_NUMBER
from .const import DEFAULT_CABLE_TYPE
from .const import DEFAULT_NAME
from .const import DOMAIN
from .exceptions import IXManagerAuthenticationError
from .exceptions import IXManagerConnectionError
from .exceptions import IXManagerNotFoundError

_LOGGER = logging.getLogger(__name__)

CABLE_TYPE_SELECTOR = SelectSelector(
    SelectSelectorConfig(
        options=list(CABLE_TYPES),
        translation_key="cable_type",
        mode=SelectSelectorMode.DROPDOWN,
    )
)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_API_KEY): str,
        vol.Required(CONF_SERIAL_NUMBER): str,
        vol.Optional(CONF_NAME, default=DEFAULT_NAME): str,
        vol.Required(
            CONF_CABLE_TYPE, default=DEFAULT_CABLE_TYPE
        ): CABLE_TYPE_SELECTOR,
    }
)

STEP_REAUTH_DATA_SCHEMA = vol.Schema({vol.Required(CONF_API_KEY): str})


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect.

    Args:
        hass: Home Assistant instance
        data: User input data

    Returns:
        Dictionary with connection info

    Raises:
        IXManagerConnectionError: If we cannot connect
        IXManagerAuthenticationError: If the API key was rejected
        IXManagerNotFoundError: If the serial number is unknown
    """
    api_client = IXManagerApiClient(hass, data[CONF_API_KEY], data[CONF_SERIAL_NUMBER])

    await api_client.async_validate_connection()

    cable_info = CABLE_TYPES[data[CONF_CABLE_TYPE]]
    return {
        "title": f"{data[CONF_NAME]} ({data[CONF_SERIAL_NUMBER]}) - {cable_info['name']}",
        "serial_number": data[CONF_SERIAL_NUMBER],
        "cable_type": data[CONF_CABLE_TYPE],
    }


class IXManagerConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for iXmanager."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step.

        Args:
            user_input: User provided configuration

        Returns:
            Flow result
        """
        errors: dict[str, str] = {}

        if user_input is not None:
            await self.async_set_unique_id(user_input[CONF_SERIAL_NUMBER])
            self._abort_if_unique_id_configured()

            try:
                info = await validate_input(self.hass, user_input)
            except IXManagerAuthenticationError:
                errors["base"] = "invalid_auth"
            except IXManagerNotFoundError:
                errors["base"] = "invalid_serial_number"
            except IXManagerConnectionError:
                errors["base"] = "cannot_connect"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                return self.async_create_entry(title=info["title"], data=user_input)

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )

    async def async_step_reauth(
        self, entry_data: Mapping[str, Any]
    ) -> ConfigFlowResult:
        """Handle reauth flow.

        Args:
            entry_data: Existing entry data

        Returns:
            Flow result
        """
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle reauth confirm step.

        Args:
            user_input: User provided configuration

        Returns:
            Flow result
        """
        errors: dict[str, str] = {}
        reauth_entry = self._get_reauth_entry()

        if user_input is not None:
            # Only the API key is re-entered; everything else stays as it was
            test_data = {
                **reauth_entry.data,
                CONF_API_KEY: user_input[CONF_API_KEY],
            }
            test_data.setdefault(CONF_NAME, DEFAULT_NAME)
            test_data.setdefault(CONF_CABLE_TYPE, DEFAULT_CABLE_TYPE)

            try:
                await validate_input(self.hass, test_data)
            except IXManagerAuthenticationError:
                errors["base"] = "invalid_auth"
            except IXManagerNotFoundError:
                errors["base"] = "invalid_serial_number"
            except IXManagerConnectionError:
                errors["base"] = "cannot_connect"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                return self.async_update_reload_and_abort(
                    reauth_entry,
                    data_updates={CONF_API_KEY: user_input[CONF_API_KEY]},
                )

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=STEP_REAUTH_DATA_SCHEMA,
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        """Create the options flow.

        Args:
            config_entry: Config entry to create options for

        Returns:
            Options flow instance
        """
        return OptionsFlowHandler()


class OptionsFlowHandler(OptionsFlow):
    """Handle options flow for iXmanager integration."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial options step.

        The cable type lives in ``entry.data`` rather than ``entry.options``,
        so it is written back with ``async_update_entry``. That fires the
        update listener registered during setup, which reloads the entry.

        Args:
            user_input: User provided options

        Returns:
            Flow result
        """
        if user_input is not None:
            self.hass.config_entries.async_update_entry(
                self.config_entry,
                data={
                    **self.config_entry.data,
                    CONF_CABLE_TYPE: user_input[CONF_CABLE_TYPE],
                },
            )
            return self.async_create_entry(title="", data={})

        current_cable_type = self.config_entry.data.get(
            CONF_CABLE_TYPE, DEFAULT_CABLE_TYPE
        )

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_CABLE_TYPE, default=current_cable_type
                    ): CABLE_TYPE_SELECTOR,
                }
            ),
        )
