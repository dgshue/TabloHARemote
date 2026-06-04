"""The Tablo Meets Home Assistant integration."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .logger import get_logger, set_debug
from .const import DOMAIN, CONF_ENABLE_DEBUG
from .coordinator import TabloCoordinator
from .services import async_setup_services, async_unload_services

_LOGGER = get_logger("tablo_remote")

PLATFORMS: list[Platform] = [Platform.MEDIA_PLAYER, Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Tablo Meets Home Assistant from a config entry."""
    _LOGGER.info("Setting up Tablo Meets Home Assistant integration (entry_id: %s)", entry.entry_id)
    hass.data.setdefault(DOMAIN, {})

    # Check if debug logging is enabled in options
    enable_debug = entry.options.get(CONF_ENABLE_DEBUG, False)
    set_debug(enable_debug)
    if enable_debug:
        _LOGGER.info("Debug logging enabled for this integration")

    # Create the coordinator and load the initial channel lineup.
    coordinator = TabloCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()
    hass.data[DOMAIN][entry.entry_id] = coordinator
    _LOGGER.debug("Coordinator created and channels loaded")

    # Set up platforms (media_player, sensor) and services.
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    async_setup_services(hass)

    # Reload the entry when options change (e.g. Roku entity / debug toggle).
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))

    _LOGGER.info("Tablo Meets Home Assistant integration initialized successfully")
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    _LOGGER.info("Unloading Tablo Meets Home Assistant integration (entry_id: %s)", entry.entry_id)
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        async_unload_services(hass)
        hass.data[DOMAIN].pop(entry.entry_id, None)

    # Disable debug logging
    set_debug(False)

    _LOGGER.info("Tablo Meets Home Assistant integration unloaded successfully")
    return unload_ok


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry."""
    await hass.config_entries.async_reload(entry.entry_id)
