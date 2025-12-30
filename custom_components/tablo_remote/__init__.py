"""The Tablo Meets Home Assistant integration."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .services import async_setup_services, async_unload_services

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Tablo Meets Home Assistant from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    # Store config entry
    hass.data[DOMAIN][entry.entry_id] = entry.data

    # Set up services
    async_setup_services(hass)

    _LOGGER.info("Tablo Meets Home Assistant integration initialized")
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    # Unload services
    async_unload_services(hass)

    # Remove from hass.data
    if DOMAIN in hass.data:
        hass.data[DOMAIN].pop(entry.entry_id, None)

    _LOGGER.info("Tablo Meets Home Assistant integration unloaded")
    return True


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry."""
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)

