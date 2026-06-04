# Tablo Meets Home Assistant

A Home Assistant custom integration for controlling **Tablo 4th generation** OTA DVR devices — change channels, fetch the channel lineup, and (optionally) drive a Roku from a cold TV all the way to watching a live channel in a single action.

## Features

- 🔌 **Cloud login** with your Tablo account (no IP/setup hunting — the device is discovered automatically).
- 📺 **`media_player` entity** with the full channel lineup as selectable sources.
- 🔢 **Current-channel sensor** showing the last channel you tuned to.
- 📡 **`set_channel` service** to tune by channel number (e.g. `2.1`) or identifier.
- 🚀 **One-call "cold TV → watching"**: when you target a Roku, `set_channel` powers on the Roku/TV, launches the Tablo app, and **deep-links straight to the live channel**.
- 🏠 **Multi-Roku aware**: one Tablo, many Rokus — send a different channel to each.
- 📋 **`get_channels` service** that returns the lineup as an action response (usable in scripts / Developer Tools).
- 🗣️ Works great behind **scripts and voice assistants** (Alexa/Google via Home Assistant Cloud).

## Installation

### HACS (recommended)

1. In HACS, open the three-dot menu → **Custom repositories**.
2. Add `https://github.com/dgshue/TabloHARemote` with category **Integration**.
3. Search for **Tablo Meets Home Assistant**, download it, and restart Home Assistant.

### Manual

1. Copy `custom_components/tablo_remote` into your Home Assistant `config/custom_components` directory.
2. Restart Home Assistant.

## Configuration

1. **Settings → Devices & Services → Add Integration** → search **Tablo Meets Home Assistant**.
2. Enter your **Tablo account email and password**. The integration logs in, discovers your device, and finishes setup.
3. (Optional) Open the integration's **Configure** (⚙️) to set:
   - **Enable debug logging** – verbose logs for troubleshooting.
   - **Roku to launch the Tablo app on** – a default Roku `media_player` used by the dashboard `media_player.tablo` source selector.

> **Login errors?** The Tablo cloud API returns a specific reason (e.g. *"Ensure this field has at least 8 characters"*). A `400` means a field failed validation (check your password/email); a `401` means wrong credentials.

## Entities

| Entity | Description |
|---|---|
| `media_player.tablo` | Source list = your channel lineup. Selecting a source tunes the Tablo (and, if a default Roku is configured, powers it on + plays the channel). |
| `sensor.tablo_current_channel` | The channel last tuned via the integration (number + name/callsign attributes). Optimistic — resets on restart. |

## Services

### `tablo_remote.set_channel`

Tune the Tablo to a channel. If a Roku is targeted, this also powers on the Roku/TV and deep-links the Tablo app straight to the live channel — getting you from a cold TV to watching in one call.

| Field | Required | Description |
|---|---|---|
| `channel_id` | one of id/number | Channel identifier, e.g. `S122912_503_01`. |
| `channel_number` | one of id/number | Channel number, e.g. `2.1`. |
| `roku_entity_id` | no | Roku `media_player` to send the channel to. Overrides the configured default. |
| `turn_on` | no (default `true`) | Power on the Roku/TV first. Only applies when a Roku is targeted. |
| `launch_app` | no (default `true`) | Launch + deep-link the Tablo app. Only applies when a Roku is targeted. |

```yaml
# Cold TV → watching 2.1 in the living room, one call
action: tablo_remote.set_channel
data:
  channel_number: "2.1"
  roku_entity_id: media_player.living_room_roku
```

```yaml
# Tune the Tablo only (no TV)
action: tablo_remote.set_channel
data:
  channel_number: "2.1"
```

**Multiple Rokus:** call `set_channel` once per Roku to put a different channel on each — the single Tablo serves each Roku independently (up to its tuner count).

### `tablo_remote.get_channels`

Returns the available channels as an action response.

```yaml
action: tablo_remote.get_channels
response_variable: tablo
# tablo.channels -> [{identifier, channel_number, name, call_sign, type, label}, ...]
```

### `tablo_remote.stop_streaming`

Placeholder — not yet implemented.

## Example: scripts & voice control

Because `set_channel` does the whole cold-start in one step, no long routine is needed. Put it in a script and expose the script to your voice assistant:

```yaml
script:
  watch_news:
    alias: Watch News
    sequence:
      - action: tablo_remote.set_channel
        data:
          channel_number: "2.1"
          roku_entity_id: media_player.living_room_roku
```

With Home Assistant Cloud, expose the script to Alexa/Google and say *"Alexa, turn on Watch News."* (Use a **script**, not an automation — voice "turn on" runs a script but only enables/disables an automation.)

## Requirements

- Home Assistant 2024.11 or later (uses the current options-flow / entity APIs).
- A Tablo **4th generation** device + Tablo account, on the same network as Home Assistant.
- **For the Roku features** (power-on / app launch / deep-link): the Home Assistant **Roku integration** installed with your Roku as a `media_player`, and the **Tablo app** installed on that Roku.

## How it works

- **Auth & lineup** come from the Tablo cloud API (`lighthousetv.ewscloud.com`).
- **Tuning** hits the local device API (`/guide/channels/{id}/watch`). Device requests carry a bare `?lh` marker and HMAC-MD5 device auth.
- **Roku playback** uses `media_player.play_media` to deep-link the Tablo Roku app (`media_type: live`, `content_id` = the channel identifier). The Tablo app id is configured in `const.py` (`TABLO_ROKU_APP_ID`); update it if your region/app differs.

## Limitations

- **Current channel is optimistic** — it reflects what the integration last commanded, not a live read from the device, and resets on restart.
- **No re-auth flow yet** — if the cloud token expires, remove and re-add the integration.
- **One Tablo per HA instance** (can be extended).
- `stop_streaming` is not implemented.

## Troubleshooting

- **Channel won't play on the Roku:** confirm the Roku integration is installed, the Roku `media_player` entity is correct, and the Tablo app is installed on that Roku. Enable debug logging in the integration options for details.
- **`set_channel` returns an error:** the integration surfaces the device/cloud message (e.g. `404 Not Found`, token errors). Check the HA log.
- **Roku app opens but doesn't change channel:** the deep-link `content_id` must be the channel's Tablo identifier; verify via `get_channels`.

## Credits

Built on insights from the [tablo2plex](https://github.com/hearhellacopters/tablo2plex) project, which documented much of the Tablo API.

## License

MIT (add a `LICENSE` file if you intend to distribute).
