"""Service definitions for Tablo Meets Home Assistant."""
from typing import Any, Dict

from homeassistant.core import (
    HomeAssistant,
    ServiceCall,
    ServiceResponse,
    SupportsResponse,
    callback,
)
from homeassistant.exceptions import HomeAssistantError

from .logger import get_logger
from .const import (
    CONF_ROKU_ENTITY,
    DOMAIN,
    SERVICE_SET_CHANNEL,
    SERVICE_GET_CHANNELS,
    SERVICE_STOP_STREAMING,
)
from .coordinator import TabloCoordinator
from .tablo_client import TabloClientError

_LOGGER = get_logger("tablo_remote.services")


def _get_coordinator(hass: HomeAssistant) -> TabloCoordinator:
    """Get the coordinator for the first configured Tablo entry."""
    entries = hass.config_entries.async_entries(DOMAIN)
    if not entries:
        raise HomeAssistantError("Tablo integration not configured")
    entry = entries[0]
    coordinator = hass.data.get(DOMAIN, {}).get(entry.entry_id)
    if coordinator is None:
        raise HomeAssistantError("Tablo integration is not loaded")
    return coordinator


@callback
def async_setup_services(hass: HomeAssistant) -> None:
    """Set up services for Tablo integration."""

    async def set_channel_service(call: ServiceCall) -> None:
        """Service to set channel on Tablo device."""
        _LOGGER.info("set_channel service called")
        channel_id = call.data.get("channel_id")
        channel_number = call.data.get("channel_number")
        roku_entity_id = call.data.get("roku_entity_id")

        coordinator = _get_coordinator(hass)
        if not coordinator.data:
            await coordinator.async_request_refresh()

        channel = coordinator.resolve_channel(
            channel_id=channel_id, channel_number=channel_number
        )
        if not channel:
            target = channel_number or channel_id or "(none provided)"
            _LOGGER.error("Channel %s not found in channel lineup", target)
            raise HomeAssistantError(f"Channel {target} not found")

        # Resolve the Roku target (call arg overrides the configured option).
        roku_entity_id = roku_entity_id or coordinator.entry.options.get(
            CONF_ROKU_ENTITY
        )
        # When a Roku is targeted, power it on and launch the app by default.
        turn_on = call.data.get("turn_on", True)
        launch_app = call.data.get("launch_app", True)

        try:
            await coordinator.async_watch(
                channel,
                roku_entity_id=roku_entity_id,
                turn_on=turn_on,
                launch_app=launch_app,
            )
            _LOGGER.info("Successfully set channel: %s", channel["identifier"])
        except TabloClientError as err:
            _LOGGER.error("Failed to set channel %s: %s", channel["identifier"], err)
            raise HomeAssistantError(f"Failed to set channel: {err}") from err

    async def get_channels_service(call: ServiceCall) -> ServiceResponse:
        """Service to get available channels, returned as a response."""
        _LOGGER.info("get_channels service called")
        coordinator = _get_coordinator(hass)
        if not coordinator.data:
            await coordinator.async_request_refresh()
        channels = coordinator.data or []
        _LOGGER.info("Returning %d available channels", len(channels))
        return {"channels": channels}

    async def stop_streaming_service(call: ServiceCall) -> None:
        """Service to stop streaming (placeholder for future implementation)."""
        _LOGGER.info("Stop streaming service called (not yet implemented)")

    # Register services
    hass.services.async_register(DOMAIN, SERVICE_SET_CHANNEL, set_channel_service)
    hass.services.async_register(
        DOMAIN,
        SERVICE_GET_CHANNELS,
        get_channels_service,
        supports_response=SupportsResponse.OPTIONAL,
    )
    hass.services.async_register(DOMAIN, SERVICE_STOP_STREAMING, stop_streaming_service)

    _LOGGER.info("Tablo services registered")


@callback
def async_unload_services(hass: HomeAssistant) -> None:
    """Unload Tablo services."""
    hass.services.async_remove(DOMAIN, SERVICE_SET_CHANNEL)
    hass.services.async_remove(DOMAIN, SERVICE_GET_CHANNELS)
    hass.services.async_remove(DOMAIN, SERVICE_STOP_STREAMING)
