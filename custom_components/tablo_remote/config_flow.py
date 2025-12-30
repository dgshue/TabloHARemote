"""Config flow for Tablo Meets Home Assistant."""
import logging
from typing import Any, Dict, Optional

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError

from .logger import get_logger
from .const import (
    DOMAIN,
    CONF_USERNAME,
    CONF_PASSWORD,
    CONF_DEVICE_URL,
    CONF_DEVICE_SERVER_ID,
    CONF_PROFILE_ID,
    CONF_LIGHTHOUSE,
    CONF_LIGHTHOUSETV_AUTHORIZATION,
    CONF_LIGHTHOUSETV_IDENTIFIER,
    CONF_UUID,
    CONF_TUNERS,
    CONF_DEVICE_NAME,
    CONF_ENABLE_DEBUG,
)
from .tablo_client import TabloClient, TabloAuthenticationError, TabloConnectionError

_LOGGER = get_logger("tablo_remote.config_flow")

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_USERNAME): str,
        vol.Required(CONF_PASSWORD): str,
    }
)

STEP_DEVICE_DATA_SCHEMA = vol.Schema(
    {
        vol.Required("device"): str,
    }
)

STEP_MANUAL_DEVICE_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_DEVICE_URL): str,
    }
)


async def validate_auth(hass: HomeAssistant, username: str, password: str) -> Dict[str, Any]:
    """Validate the user credentials and return credentials dict."""
    _LOGGER.info("Validating authentication for user: %s", username)
    try:
        credentials = await TabloClient.authenticate(username, password)
        _LOGGER.info("Authentication validation successful")
        return credentials
    except TabloAuthenticationError as err:
        _LOGGER.error("Authentication validation failed: %s", err)
        raise InvalidAuth from err
    # Note: TabloConnectionError is no longer raised during authentication
    # since device verification is now optional


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Tablo Meets Home Assistant."""

    VERSION = 1

    def __init__(self):
        """Initialize config flow."""
        self.credentials: Optional[Dict[str, Any]] = None
        self.devices: list = []
        self.profiles: list = []

    async def async_step_user(
        self, user_input: Optional[Dict[str, Any]] = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: Dict[str, str] = {}

        if user_input is not None:
            _LOGGER.info("Starting configuration flow for user: %s", user_input[CONF_USERNAME])
            try:
                # Validate authentication
                _LOGGER.debug("Validating credentials...")
                self.credentials = await validate_auth(
                    self.hass, user_input[CONF_USERNAME], user_input[CONF_PASSWORD]
                )
                _LOGGER.debug("Credentials validated, processing device information")

                # Get devices and profiles from credentials
                # For now, we use the first device and profile from authentication
                # In future, we could add a step to select from multiple
                device = self.credentials.get("device", {})
                profile = self.credentials.get("profile", {})
                device_url = device.get("url", "")
                device_server_id = device.get("serverId", "")

                # Check if already configured (use server ID as unique ID)
                await self.async_set_unique_id(device_server_id)
                self._abort_if_unique_id_configured()

                _LOGGER.info(
                    "Creating config entry for device: %s (Server ID: %s)",
                    device.get("name", "Device"),
                    device_server_id,
                )

                # Store the credentials (password not stored, only tokens)
                config_data = {
                    CONF_USERNAME: user_input[CONF_USERNAME],  # Store username for reference
                    CONF_DEVICE_URL: device_url,
                    CONF_DEVICE_SERVER_ID: device_server_id,
                    CONF_PROFILE_ID: profile.get("identifier", ""),
                    CONF_LIGHTHOUSE: self.credentials.get("lighthouse", ""),
                    CONF_LIGHTHOUSETV_AUTHORIZATION: self.credentials.get(
                        "lighthousetv_authorization", ""
                    ),
                    CONF_LIGHTHOUSETV_IDENTIFIER: self.credentials.get(
                        "lighthousetv_identifier", ""
                    ),
                    CONF_UUID: self.credentials.get("uuid", ""),
                    CONF_TUNERS: self.credentials.get("tuners", 2),
                    CONF_DEVICE_NAME: device.get("name", "Tablo Device"),
                }
                _LOGGER.debug("Config entry data prepared (sensitive data redacted)")

                _LOGGER.info("Configuration flow completed successfully")
                return self.async_create_entry(
                    title=f"Tablo {device.get('name', 'Device')}",
                    data=config_data,
                )
            except InvalidAuth as err:
                _LOGGER.error("Invalid auth error in config flow: %s", err)
                errors["base"] = "invalid_auth"
            except Exception as err:
                _LOGGER.exception("Unexpected error in config flow: %s", err)
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Get the options flow for this handler."""
        return OptionsFlowHandler(config_entry)


class OptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options flow."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(self, user_input: Optional[Dict[str, Any]] = None) -> FlowResult:
        """Manage the options."""
        from .logger import set_debug

        if user_input is not None:
            _LOGGER.info("Options updated: enable_debug=%s", user_input.get(CONF_ENABLE_DEBUG, False))
            # Update debug logging based on option
            set_debug(user_input.get(CONF_ENABLE_DEBUG, False))
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({
                vol.Optional(
                    CONF_ENABLE_DEBUG,
                    default=self.config_entry.options.get(CONF_ENABLE_DEBUG, False),
                ): bool,
            }),
        )


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""

    pass


class InvalidAuth(HomeAssistantError):
    """Error to indicate there is invalid auth."""

    pass

