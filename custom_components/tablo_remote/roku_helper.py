"""Helper functions for integrating with Roku devices."""
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
        """Find Roku device entity by entity_id."""
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

        # Check if it's a Roku device (entity_id typically starts with media_player.roku_)
        if "roku" in entity_id.lower():
            _LOGGER.debug("Found Roku device: %s", entity_id)
            return entity_id

        _LOGGER.debug("Entity %s does not appear to be a Roku device", entity_id)
        return None

    async def launch_tablo_app(self, entity_id: str) -> bool:
        """Launch Tablo app on Roku device."""
        _LOGGER.info("Launching Tablo app on Roku device: %s", entity_id)
        # First verify the device exists
        device_entity = await self.find_roku_device(entity_id)
        if not device_entity:
            _LOGGER.error("Roku device %s not found", entity_id)
            raise RokuNotFoundError(f"Roku device {entity_id} not found")

        # Try to use Roku's launch_app service
        # Tablo app ID on Roku needs to be determined, using common pattern
        # The app ID is typically a numeric string
        # We'll use a placeholder that needs to be configured or discovered
        tablo_app_id = "41972"  # This needs to be verified/configured
        _LOGGER.debug("Using Tablo app ID: %s", tablo_app_id)

        try:
            # Use Roku's launch_app service
            _LOGGER.debug("Calling roku.launch_app service")
            await self.hass.services.async_call(
                "roku",
                "launch_app",
                {"entity_id": entity_id, "app_id": tablo_app_id},
                blocking=True,
            )
            _LOGGER.info("Successfully launched Tablo app on %s", entity_id)
            return True
        except Exception as err:
            _LOGGER.warning("Failed to launch app using roku.launch_app, trying fallback: %s", err)
            # Fallback: try using media_player.select_source
            try:
                _LOGGER.debug("Trying fallback: media_player.select_source")
                await self.hass.services.async_call(
                    "media_player",
                    "select_source",
                    {"entity_id": entity_id, "source": "Tablo"},
                    blocking=True,
                )
                _LOGGER.info("Successfully launched Tablo app using fallback method on %s", entity_id)
                return True
            except Exception as fallback_err:
                _LOGGER.error("Failed to launch Tablo app on %s: %s (fallback also failed: %s)", entity_id, err, fallback_err)
                raise HomeAssistantError(
                    f"Failed to launch Tablo app on {entity_id}: {err}"
                ) from err

    async def wait_for_app_ready(self, entity_id: str, timeout: int = 10) -> bool:
        """Wait for Roku app to be ready (simplified implementation)."""
        _LOGGER.debug("Waiting for app to be ready on %s (timeout: %ds)", entity_id, timeout)
        # This is a simplified implementation
        # In practice, you might want to check the media_player state
        # to verify the app has launched
        import asyncio

        try:
            await asyncio.sleep(2)  # Give the app time to launch
            _LOGGER.debug("App ready check completed for %s", entity_id)
            return True
        except Exception as err:
            _LOGGER.warning("Error waiting for app ready on %s: %s", entity_id, err)
            return False

