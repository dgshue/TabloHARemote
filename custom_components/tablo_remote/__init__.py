"""The Tablo Meets Home Assistant integration."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .logger import get_logger, set_debug
from .const import DOMAIN, CONF_ENABLE_DEBUG
from .services import async_setup_services, async_unload_services

_LOGGER = get_logger("tablo_remote")


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Tablo Meets Home Assistant from a config entry."""
    _LOGGER.info("Setting up Tablo Meets Home Assistant integration (entry_id: %s)", entry.entry_id)
    hass.data.setdefault(DOMAIN, {})

    # Check if debug logging is enabled in options
    enable_debug = entry.options.get(CONF_ENABLE_DEBUG, False)
    if enable_debug:
        _LOGGER.info("Debug logging enabled for this integration")
        set_debug(True)
    else:
        set_debug(False)

    # Store config entry
    hass.data[DOMAIN][entry.entry_id] = entry.data
    _LOGGER.debug("Config entry data stored")

    # Set up services
    async_setup_services(hass)

    _LOGGER.info("Tablo Meets Home Assistant integration initialized successfully")
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    _LOGGER.info("Unloading Tablo Meets Home Assistant integration (entry_id: %s)", entry.entry_id)
    # Unload services
    async_unload_services(hass)

    # Remove from hass.data
    if DOMAIN in hass.data:
        hass.data[DOMAIN].pop(entry.entry_id, None)

    # Disable debug logging
    set_debug(False)

    _LOGGER.info("Tablo Meets Home Assistant integration unloaded successfully")
    return True


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry."""
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)

