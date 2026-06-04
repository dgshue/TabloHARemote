"""Data update coordinator for Tablo Meets Home Assistant."""
from __future__ import annotations

from datetime import timedelta
from typing import Any, Dict, List, Optional

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .logger import get_logger
from .const import (
    CONF_DEVICE_URL,
    CONF_LIGHTHOUSE,
    CONF_LIGHTHOUSETV_AUTHORIZATION,
    CONF_UUID,
    DOMAIN,
)
from .tablo_client import TabloClient, TabloClientError

_LOGGER = get_logger("tablo_remote.coordinator")

# Channel lineup changes rarely; poll the cloud a few times a day.
UPDATE_INTERVAL = timedelta(hours=6)


def normalize_channel(channel: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Flatten a raw cloud channel into a simple dict, or None if unusable."""
    kind = channel.get("kind")
    data = channel.get(kind) if kind in ("ota", "ott") else None
    if not data:
        return None
    major = data.get("major")
    minor = data.get("minor")
    if major is None or minor is None:
        return None
    number = f"{major}.{minor}"
    call_sign = data.get("callSign", "") or ""
    name = channel.get("name", "") or call_sign or number
    return {
        "identifier": channel.get("identifier", ""),
        "channel_number": number,
        "name": name,
        "call_sign": call_sign,
        "type": kind,
        # Human-friendly, unique label used for media_player source selection.
        "label": f"{number} - {call_sign or name}",
    }


class TabloCoordinator(DataUpdateCoordinator[List[Dict[str, Any]]]):
    """Fetch the channel lineup and track the (optimistic) current channel."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass, _LOGGER, name=DOMAIN, update_interval=UPDATE_INTERVAL
        )
        self.entry = entry
        self.client = TabloClient(
            {
                "device": {"url": entry.data.get(CONF_DEVICE_URL)},
                "uuid": entry.data.get(CONF_UUID),
                "lighthouse": entry.data.get(CONF_LIGHTHOUSE),
                "lighthousetv_authorization": entry.data.get(
                    CONF_LIGHTHOUSETV_AUTHORIZATION
                ),
            }
        )
        self.channels_by_label: Dict[str, Dict[str, Any]] = {}
        self.channels_by_number: Dict[str, Dict[str, Any]] = {}
        self.channels_by_id: Dict[str, Dict[str, Any]] = {}
        # Optimistic: the channel we last told the device to tune to.
        self.current_channel: Optional[Dict[str, Any]] = None

    async def _async_update_data(self) -> List[Dict[str, Any]]:
        """Fetch and normalize the channel lineup from the cloud API."""
        try:
            raw = await self.client.get_channels()
        except TabloClientError as err:
            raise UpdateFailed(f"Error fetching channels: {err}") from err

        channels: List[Dict[str, Any]] = []
        for raw_channel in raw:
            channel = normalize_channel(raw_channel)
            if channel and channel["identifier"]:
                channels.append(channel)

        self.channels_by_label = {c["label"]: c for c in channels}
        self.channels_by_number = {c["channel_number"]: c for c in channels}
        self.channels_by_id = {c["identifier"]: c for c in channels}
        _LOGGER.debug("Coordinator loaded %d channels", len(channels))
        return channels

    def resolve_channel(
        self,
        channel_id: Optional[str] = None,
        channel_number: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Resolve a normalized channel by identifier or number."""
        if channel_id:
            cached = self.channels_by_id.get(channel_id)
            if cached:
                return cached
            # Allow tuning an identifier that isn't in the cached lineup.
            return {
                "identifier": channel_id,
                "channel_number": "",
                "name": channel_id,
                "call_sign": "",
                "type": "",
                "label": channel_id,
            }
        if channel_number:
            return self.channels_by_number.get(channel_number)
        return None

    async def async_set_channel(self, channel: Dict[str, Any]) -> None:
        """Tune the device to a channel and update the current-channel state."""
        await self.client.watch_channel(channel["identifier"])
        self.current_channel = channel
        self.async_update_listeners()
