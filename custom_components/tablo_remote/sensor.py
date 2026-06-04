"""Sensor entities for Tablo Meets Home Assistant."""
from __future__ import annotations

from typing import Any, Dict, Optional

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .logger import get_logger
from .const import CONF_DEVICE_NAME, CONF_DEVICE_SERVER_ID, DOMAIN
from .coordinator import TabloCoordinator

_LOGGER = get_logger("tablo_remote.sensor")


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Tablo sensors from a config entry."""
    coordinator: TabloCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([TabloCurrentChannelSensor(coordinator, entry)])


class TabloCurrentChannelSensor(CoordinatorEntity[TabloCoordinator], SensorEntity):
    """Show the channel the Tablo was last told to tune to."""

    _attr_has_entity_name = True
    _attr_name = "Current channel"
    _attr_icon = "mdi:television-classic"

    def __init__(self, coordinator: TabloCoordinator, entry: ConfigEntry) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        server_id = entry.data.get(CONF_DEVICE_SERVER_ID) or entry.entry_id
        self._attr_unique_id = f"{server_id}_current_channel"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, server_id)},
            name=entry.data.get(CONF_DEVICE_NAME, "Tablo"),
            manufacturer="Tablo",
            model="Tablo 4th Gen",
        )

    @property
    def native_value(self) -> Optional[str]:
        """Return the current channel number."""
        current = self.coordinator.current_channel
        if not current:
            return None
        return current.get("channel_number") or current.get("label")

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return details about the current channel."""
        current = self.coordinator.current_channel
        if not current:
            return {}
        return {
            "identifier": current.get("identifier"),
            "name": current.get("name"),
            "call_sign": current.get("call_sign"),
            "type": current.get("type"),
        }
