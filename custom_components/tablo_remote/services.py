"""Service definitions for Tablo Meets Home Assistant."""
from typing import Any, Dict

from homeassistant.core import HomeAssistant, ServiceCall, callback
from homeassistant.exceptions import HomeAssistantError

from .logger import get_logger
from .const import (
    DOMAIN,
    SERVICE_SET_CHANNEL,
    SERVICE_GET_CHANNELS,
    SERVICE_STOP_STREAMING,
)
from .roku_helper import RokuHelper, RokuNotFoundError
from .tablo_client import TabloClient, TabloClientError

_LOGGER = get_logger("tablo_remote.services")


def _get_config_entry(hass: HomeAssistant):
    """Get the first Tablo config entry."""
    entries = hass.config_entries.async_entries(DOMAIN)
    if not entries:
        raise HomeAssistantError("Tablo integration not configured")
    return entries[0]


@callback
def async_setup_services(hass: HomeAssistant) -> None:
    """Set up services for Tablo integration."""

    async def set_channel_service(call: ServiceCall) -> None:
        """Service to set channel on Tablo device."""
        _LOGGER.info("set_channel service called")
        channel_id = call.data.get("channel_id")
        channel_number = call.data.get("channel_number")
        roku_entity_id = call.data.get("roku_entity_id")

        _LOGGER.debug(
            "Service parameters: channel_id=%s, channel_number=%s, roku_entity_id=%s",
            channel_id,
            channel_number,
            roku_entity_id,
        )

        # Get the config entry
        entry = _get_config_entry(hass)
        _LOGGER.debug("Using config entry: %s", entry.entry_id)

        # Build credentials from config entry
        credentials = {
            "device": {"url": entry.data.get("device_url")},
            "uuid": entry.data.get("uuid"),
            "lighthouse": entry.data.get("lighthouse"),
            "lighthousetv_authorization": entry.data.get("lighthousetv_authorization"),
        }

        client = TabloClient(credentials)

        # If channel_number is provided, look up channel_id
        if channel_number and not channel_id:
            _LOGGER.debug("Looking up channel_id for channel_number: %s", channel_number)
            try:
                channels = await client.get_channels()
                _LOGGER.debug("Retrieved %d channels for lookup", len(channels))
                # Find channel by number (format: major.minor)
                for channel in channels:
                    if channel.get("kind") == "ota":
                        chan_num = f'{channel["ota"]["major"]}.{channel["ota"]["minor"]}'
                        if chan_num == channel_number:
                            channel_id = channel["identifier"]
                            _LOGGER.debug(
                                "Found channel_id %s for channel_number %s",
                                channel_id,
                                channel_number,
                            )
                            break
                    elif channel.get("kind") == "ott":
                        chan_num = f'{channel["ott"]["major"]}.{channel["ott"]["minor"]}'
                        if chan_num == channel_number:
                            channel_id = channel["identifier"]
                            _LOGGER.debug(
                                "Found channel_id %s for channel_number %s",
                                channel_id,
                                channel_number,
                            )
                            break
                if not channel_id:
                    _LOGGER.error("Channel number %s not found in channel lineup", channel_number)
                    raise HomeAssistantError(f"Channel {channel_number} not found")
            except TabloClientError as err:
                _LOGGER.error("Failed to get channels: %s", err)
                raise HomeAssistantError(f"Failed to get channels: {err}") from err

        if not channel_id:
            _LOGGER.error("Neither channel_id nor channel_number provided")
            raise HomeAssistantError("channel_id or channel_number required")

        # Launch Tablo app on Roku if entity_id provided
        if roku_entity_id:
            roku_helper = RokuHelper(hass)
            try:
                await roku_helper.launch_tablo_app(roku_entity_id)
                await roku_helper.wait_for_app_ready(roku_entity_id)
            except RokuNotFoundError as err:
                _LOGGER.warning(f"Roku device not found: {err}")
            except Exception as err:
                _LOGGER.warning(f"Failed to launch Tablo app on Roku: {err}")

        # Set channel on Tablo device
        try:
            _LOGGER.debug("Calling watch_channel for channel_id: %s", channel_id)
            await client.watch_channel(channel_id)
            _LOGGER.info("Successfully set channel: %s", channel_id)
        except TabloClientError as err:
            _LOGGER.error("Failed to set channel %s: %s", channel_id, err)
            raise HomeAssistantError(f"Failed to set channel: {err}") from err

    async def get_channels_service(call: ServiceCall) -> None:
        """Service to get available channels."""
        _LOGGER.info("get_channels service called")
        # Get the config entry
        entry = _get_config_entry(hass)
        _LOGGER.debug("Using config entry: %s", entry.entry_id)

        # Build credentials from config entry
        credentials = {
            "device": {"url": entry.data.get("device_url")},
            "uuid": entry.data.get("uuid"),
            "lighthouse": entry.data.get("lighthouse"),
            "lighthousetv_authorization": entry.data.get("lighthousetv_authorization"),
        }

        client = TabloClient(credentials)
        _LOGGER.debug("TabloClient created for get_channels")

        try:
            _LOGGER.debug("Fetching channels from Tablo device")
            channels = await client.get_channels()
            # Format channels and log them
            result = []
            for channel in channels:
                if channel.get("kind") == "ota":
                    result.append(
                        {
                            "identifier": channel["identifier"],
                            "name": channel.get("name", ""),
                            "channel_number": f'{channel["ota"]["major"]}.{channel["ota"]["minor"]}',
                            "type": "ota",
                            "call_sign": channel["ota"].get("callSign", ""),
                        }
                    )
                elif channel.get("kind") == "ott":
                    result.append(
                        {
                            "identifier": channel["identifier"],
                            "name": channel.get("name", ""),
                            "channel_number": f'{channel["ott"]["major"]}.{channel["ott"]["minor"]}',
                            "type": "ott",
                            "call_sign": channel["ott"].get("callSign", ""),
                        }
                    )
            _LOGGER.info("Retrieved %d available channels", len(result))
            _LOGGER.debug("Available channels: %s", result)
        except TabloClientError as err:
            _LOGGER.error("Failed to get channels: %s", err)
            raise HomeAssistantError(f"Failed to get channels: {err}") from err

    async def stop_streaming_service(call: ServiceCall) -> None:
        """Service to stop streaming (placeholder for future implementation)."""
        _LOGGER.info("Stop streaming service called (not yet implemented)")

    # Register services
    hass.services.async_register(DOMAIN, SERVICE_SET_CHANNEL, set_channel_service)
    hass.services.async_register(DOMAIN, SERVICE_GET_CHANNELS, get_channels_service)
    hass.services.async_register(DOMAIN, SERVICE_STOP_STREAMING, stop_streaming_service)

    _LOGGER.info("Tablo services registered")


@callback
def async_unload_services(hass: HomeAssistant) -> None:
    """Unload Tablo services."""
    hass.services.async_remove(DOMAIN, SERVICE_SET_CHANNEL)
    hass.services.async_remove(DOMAIN, SERVICE_GET_CHANNELS)
    hass.services.async_remove(DOMAIN, SERVICE_STOP_STREAMING)

