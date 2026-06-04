"""Helper functions for integrating with Roku devices."""
import asyncio
from typing import Optional

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError

from .logger import get_logger

_LOGGER = get_logger("tablo_remote.roku_helper")


class RokuNotFoundError(HomeAssistantError):
    """Error when Roku device is not found."""

    pass


class RokuHelper:
    """Helper class for Roku integration."""

    def __init__(self, hass: HomeAssistant):
        """Initialize Roku helper."""
        self.hass = hass

    async def find_roku_device(self, entity_id: str) -> Optional[str]:
        """Validate the targeted Roku media_player entity by entity_id.

        The caller explicitly chooses which Roku to use, so we only verify the
        entity exists and is a media_player — we do NOT require "roku" in the
        name (Roku TVs are often named e.g. media_player.living_room_tv).
        """
        _LOGGER.debug("Looking for Roku device: %s", entity_id)
        # Check if entity exists in the state machine
        state = self.hass.states.get(entity_id)
        if state is None:
            _LOGGER.warning("Entity %s not found in state machine", entity_id)
            return None

        # Verify it's a media_player entity (Roku devices are media players)
        if not entity_id.startswith("media_player."):
            _LOGGER.warning("Entity %s is not a media_player entity", entity_id)
            return None

        _LOGGER.debug("Using Roku target: %s", entity_id)
        return entity_id

    async def power_on(self, entity_id: str, settle_seconds: int = 3) -> bool:
        """Power on the Roku (and the TV via HDMI-CEC). Best-effort."""
        _LOGGER.info("Powering on Roku device: %s", entity_id)
        try:
            await self.hass.services.async_call(
                "media_player",
                "turn_on",
                {"entity_id": entity_id},
                blocking=True,
            )
            # Give the Roku/TV a moment to wake before launching an app.
            await asyncio.sleep(settle_seconds)
            _LOGGER.debug("Power-on completed for %s", entity_id)
            return True
        except Exception as err:  # noqa: BLE001 - best-effort
            _LOGGER.warning("Failed to power on %s: %s", entity_id, err)
            return False

    def _find_tablo_source(self, entity_id: str) -> Optional[str]:
        """Find the Tablo app's name in a Roku's installed-app (source) list."""
        state = self.hass.states.get(entity_id)
        source_list = (state.attributes.get("source_list") or []) if state else []
        # The app is named "Tablo" or "Tablo TV" depending on the device.
        return next((s for s in source_list if "tablo" in s.lower()), None)

    async def launch_tablo_app(self, entity_id: str) -> bool:
        """Launch the Tablo app on a Roku via media_player.select_source.

        The app name is discovered from the device's own source_list (e.g.
        "Tablo TV"), so there is no dependency on a hardcoded app id. Modern
        HA's Roku integration launches apps via select_source, not a
        roku.launch_app service.
        """
        _LOGGER.info("Launching Tablo app on Roku device: %s", entity_id)
        device_entity = await self.find_roku_device(entity_id)
        if not device_entity:
            _LOGGER.error("Roku device %s not found", entity_id)
            raise RokuNotFoundError(f"Roku device {entity_id} not found")

        tablo_source = self._find_tablo_source(entity_id)
        if not tablo_source:
            tablo_source = "Tablo TV"  # sensible default if app list unavailable
            _LOGGER.debug(
                "No Tablo app found in %s source_list; defaulting to '%s'",
                entity_id, tablo_source,
            )

        try:
            await self.hass.services.async_call(
                "media_player",
                "select_source",
                {"entity_id": entity_id, "source": tablo_source},
                blocking=True,
            )
            _LOGGER.info("Launched '%s' on %s", tablo_source, entity_id)
            return True
        except Exception as err:  # noqa: BLE001
            _LOGGER.error("Failed to launch Tablo app on %s: %s", entity_id, err)
            raise HomeAssistantError(
                f"Failed to launch Tablo app on {entity_id}: {err}"
            ) from err

    async def wait_for_app_ready(self, entity_id: str, timeout: int = 10) -> bool:
        """Wait for Roku app to be ready (simplified implementation)."""
        _LOGGER.debug("Waiting for app to be ready on %s (timeout: %ds)", entity_id, timeout)
        # This is a simplified implementation
        # In practice, you might want to check the media_player state
        # to verify the app has launched
        try:
            await asyncio.sleep(2)  # Give the app time to launch
            _LOGGER.debug("App ready check completed for %s", entity_id)
            return True
        except Exception as err:
            _LOGGER.warning("Error waiting for app ready on %s: %s", entity_id, err)
            return False

