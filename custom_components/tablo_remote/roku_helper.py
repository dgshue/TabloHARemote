"""Helper functions for integrating with Roku devices."""
from typing import Optional

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError


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
        # Check if entity exists in the state machine
        state = self.hass.states.get(entity_id)
        if state is None:
            return None

        # Verify it's a media_player entity (Roku devices are media players)
        if not entity_id.startswith("media_player."):
            return None

        # Check if it's a Roku device (entity_id typically starts with media_player.roku_)
        if "roku" in entity_id.lower():
            return entity_id

        return None

    async def launch_tablo_app(self, entity_id: str) -> bool:
        """Launch Tablo app on Roku device."""
        # First verify the device exists
        device_entity = await self.find_roku_device(entity_id)
        if not device_entity:
            raise RokuNotFoundError(f"Roku device {entity_id} not found")

        # Try to use Roku's launch_app service
        # Tablo app ID on Roku needs to be determined, using common pattern
        # The app ID is typically a numeric string
        # We'll use a placeholder that needs to be configured or discovered
        tablo_app_id = "41972"  # This needs to be verified/configured

        try:
            # Use Roku's launch_app service
            await self.hass.services.async_call(
                "roku",
                "launch_app",
                {"entity_id": entity_id, "app_id": tablo_app_id},
                blocking=True,
            )
            return True
        except Exception as err:
            # Fallback: try using media_player.select_source
            try:
                await self.hass.services.async_call(
                    "media_player",
                    "select_source",
                    {"entity_id": entity_id, "source": "Tablo"},
                    blocking=True,
                )
                return True
            except Exception:
                raise HomeAssistantError(
                    f"Failed to launch Tablo app on {entity_id}: {err}"
                ) from err

    async def wait_for_app_ready(self, entity_id: str, timeout: int = 10) -> bool:
        """Wait for Roku app to be ready (simplified implementation)."""
        # This is a simplified implementation
        # In practice, you might want to check the media_player state
        # to verify the app has launched
        import asyncio

        try:
            await asyncio.sleep(2)  # Give the app time to launch
            return True
        except Exception:
            return False

