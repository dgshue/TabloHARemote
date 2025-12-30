# Tablo Meets Home Assistant

Home Assistant integration for controlling Tablo 4th generation devices and launching the Tablo app on Roku devices.

## Features

- Control Tablo devices from Home Assistant
- Launch Tablo app on Roku devices
- Set channels on Tablo devices via automations
- Get available channel lineup
- Integrates with existing Roku integration

## Installation

### HACS (Recommended)

1. Open HACS in Home Assistant
2. Go to Integrations
3. Click the three dots menu (⋮) and select "Custom repositories"
4. Add this repository URL
5. Search for "Tablo Meets Home Assistant" and install

### Manual Installation

1. Copy the `tablo_remote` folder to `custom_components` in your Home Assistant configuration directory
2. Restart Home Assistant
3. Go to Settings → Devices & Services → Add Integration
4. Search for "Tablo Meets Home Assistant"

## Configuration

1. Go to Settings → Devices & Services → Add Integration
2. Search for "Tablo Meets Home Assistant"
3. Enter your Tablo account email and password
4. The integration will automatically discover your Tablo device and complete setup

## Usage

### Services

The integration provides the following services:

#### `tablo_remote.set_channel`

Set a channel on your Tablo device and optionally launch the Tablo app on a Roku device.

**Service Data:**
- `channel_id` (string, optional): The channel identifier (e.g., "S122912_503_01")
- `channel_number` (string, optional): The channel number (e.g., "2.1" or "4.2")
- `roku_entity_id` (string, optional): The entity ID of your Roku device (e.g., "media_player.roku_living_room")

**Note:** Either `channel_id` or `channel_number` must be provided.

**Example:**
```yaml
service: tablo_remote.set_channel
data:
  channel_number: "2.1"
  roku_entity_id: media_player.roku_living_room
```

#### `tablo_remote.get_channels`

Get the list of available channels from your Tablo device.

**Service Data:** None

**Response:**
```json
{
  "channels": [
    {
      "identifier": "S122912_503_01",
      "name": "Channel Name",
      "channel_number": "2.1",
      "type": "ota",
      "call_sign": "CALL"
    }
  ]
}
```

#### `tablo_remote.stop_streaming`

Stop the current stream (placeholder for future implementation).

### Automations

Example automation to change channel:

```yaml
automation:
  - alias: "Change to Channel 2.1 on Tablo"
    trigger:
      - platform: event
        event_type: button_pressed
        event_data:
          button: channel_2
    action:
      - service: tablo_remote.set_channel
        data:
          channel_number: "2.1"
          roku_entity_id: media_player.roku_living_room
```

## Requirements

- Home Assistant 2023.1.0 or later
- Tablo 4th generation device
- Tablo account
- Roku device with Tablo app installed (optional, for Roku integration)

## Troubleshooting

### Cannot Connect to Device

- Ensure your Tablo device is on the same network as Home Assistant
- Check that the device URL is correct (can be found in Tablo app settings)
- Verify your Tablo account credentials are correct

### Roku App Not Launching

- Ensure the Roku integration is installed and configured
- Verify the Roku entity ID is correct
- Check that the Tablo app is installed on your Roku device

## Limitations

- Currently supports one Tablo device per Home Assistant instance (can be extended)
- Channel changing on Tablo device should trigger Roku app to update (behavior needs verification)
- Stop streaming service is not yet fully implemented

## Support

For issues, feature requests, or questions:
- Open an issue on GitHub
- Check the [Home Assistant Community Forum](https://community.home-assistant.io/)

## Credits

This integration is based on the [tablo2plex](https://github.com/hearhellacopters/tablo2plex) project, which provided valuable insights into the Tablo API.

## License

[Add your license here]

