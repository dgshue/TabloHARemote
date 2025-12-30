"""Constants for the Tablo Meets Home Assistant integration."""
from typing import Final

DOMAIN: Final = "tablo_remote"
INTEGRATION_NAME: Final = "Tablo Meets Home Assistant"

# Cloud API
CLOUD_API_HOST: Final = "lighthousetv.ewscloud.com"
CLOUD_API_PORT: Final = 443
LOGIN_PATH: Final = "/api/v2/login/"
ACCOUNT_PATH: Final = "/api/v2/account/"
ACCOUNT_SELECT_PATH: Final = "/api/v2/account/select/"
CHANNELS_PATH: Final = "/api/v2/account/{lighthouse}/guide/channels/"
AIRINGS_PATH: Final = "/api/v2/account/guide/channels/{channel_id}/airings/{date}/"

# Local Device API
SERVER_INFO_PATH: Final = "/server/info"
WATCH_CHANNEL_PATH: Final = "/guide/channels/{channel_id}/watch"

# HTTP Headers
USER_AGENT: Final = "Tablo-FAST/2.0.0 (Mobile; iPhone; iOS 16.6)"
ACCEPT_HEADER: Final = "*/*"
CONTENT_TYPE_JSON: Final = "application/json"
CONTENT_TYPE_FORM: Final = "application/x-www-form-urlencoded"

# Device Authentication Keys (from tablo2plex source)
DEVICE_KEY: Final = "ljpg6ZkwShVv8aI12E2LP55Ep8vq1uYDPvX0DdTB"
HASH_KEY: Final = "6l8jU5N43cEilqItmT3U2M2PFM3qPziilXqau9ys"

# Defaults
DEFAULT_TIMEOUT: Final = 30
DEFAULT_REQUEST_TIMEOUT: Final = 10

# Service Names
SERVICE_SET_CHANNEL: Final = "set_channel"
SERVICE_GET_CHANNELS: Final = "get_channels"
SERVICE_STOP_STREAMING: Final = "stop_streaming"

# Config Flow
CONF_USERNAME: Final = "username"
CONF_PASSWORD: Final = "password"
CONF_DEVICE_URL: Final = "device_url"
CONF_DEVICE_SERVER_ID: Final = "device_server_id"
CONF_PROFILE_ID: Final = "profile_id"
CONF_LIGHTHOUSE: Final = "lighthouse"
CONF_LIGHTHOUSETV_AUTHORIZATION: Final = "lighthousetv_authorization"
CONF_LIGHTHOUSETV_IDENTIFIER: Final = "lighthousetv_identifier"
CONF_UUID: Final = "uuid"
CONF_TUNERS: Final = "tuners"
CONF_DEVICE_NAME: Final = "device_name"
CONF_ENABLE_DEBUG: Final = "enable_debug"

