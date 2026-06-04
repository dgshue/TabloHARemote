"""Media player entity for Tablo Meets Home Assistant."""
from __future__ import annotations

from typing import List, Optional

from homeassistant.components.media_player import (
    MediaPlayerEntity,
    MediaPlayerEntityFeature,
    MediaPlayerState,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .logger import get_logger
from .const import (
    CONF_DEVICE_NAME,
    CONF_DEVICE_SERVER_ID,
    CONF_ROKU_ENTITY,
    DOMAIN,
)
from .coordinator import TabloCoordinator

_LOGGER = get_logger("tablo_remote.media_player")


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Tablo media player from a config entry."""
    coordinator: TabloCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([TabloMediaPlayer(coordinator, entry)])


class TabloMediaPlayer(CoordinatorEntity[TabloCoordinator], MediaPlayerEntity):
    """Represent the Tablo as a media player with channel selection."""

    _attr_has_entity_name = True
    _attr_name = None
    _attr_supported_features = MediaPlayerEntityFeature.SELECT_SOURCE

    def __init__(self, coordinator: TabloCoordinator, entry: ConfigEntry) -> None:
        """Initialize the media player."""
        super().__init__(coordinator)
        self._entry = entry
        server_id = entry.data.get(CONF_DEVICE_SERVER_ID) or entry.entry_id
        self._attr_unique_id = f"{server_id}_media_player"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, server_id)},
            name=entry.data.get(CONF_DEVICE_NAME, "Tablo"),
            manufacturer="Tablo",
            model="Tablo 4th Gen",
        )

    @property
    def state(self) -> MediaPlayerState:
        """Return PLAYING once a channel has been selected, else IDLE."""
        return (
            MediaPlayerState.PLAYING
            if self.coordinator.current_channel
            else MediaPlayerState.IDLE
        )

    @property
    def source_list(self) -> List[str]:
        """Return the list of selectable channels."""
        return [channel["label"] for channel in (self.coordinator.data or [])]

    @property
    def source(self) -> Optional[str]:
        """Return the currently selected channel label."""
        current = self.coordinator.current_channel
        return current["label"] if current else None

    async def async_select_source(self, source: str) -> None:
        """Tune the Tablo (and optionally the Roku) to the selected channel."""
        channel = self.coordinator.channels_by_label.get(source)
        if not channel:
            _LOGGER.error("Unknown source selected: %s", source)
            return

        # When a default Roku is configured, power it on + launch the app too.
        roku_entity = self._entry.options.get(CONF_ROKU_ENTITY)
        await self.coordinator.async_watch(
            channel,
            roku_entity_id=roku_entity,
            turn_on=bool(roku_entity),
            launch_app=bool(roku_entity),
        )
