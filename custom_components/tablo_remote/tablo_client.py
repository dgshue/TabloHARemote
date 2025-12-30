"""Tablo API client for communicating with Tablo devices."""
import asyncio
import hashlib
import hmac
import json
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

import aiohttp
from aiohttp import ClientSession, ClientTimeout, TCPConnector
from urllib.parse import urljoin

from .logger import get_logger, is_debug_enabled, log_sensitive_data
from .const import (
    ACCEPT_HEADER,
    AIRINGS_PATH,
    CHANNELS_PATH,
    CLOUD_API_HOST,
    CLOUD_API_PORT,
    CONTENT_TYPE_FORM,
    CONTENT_TYPE_JSON,
    DEVICE_KEY,
    HASH_KEY,
    SERVER_INFO_PATH,
    USER_AGENT,
    WATCH_CHANNEL_PATH,
    ACCOUNT_PATH,
    ACCOUNT_SELECT_PATH,
    LOGIN_PATH,
    DEFAULT_TIMEOUT,
    DEFAULT_REQUEST_TIMEOUT,
)

_LOGGER = get_logger("tablo_remote.tablo_client")


class TabloClientError(Exception):
    """Base exception for Tablo client errors."""

    pass


class TabloAuthenticationError(TabloClientError):
    """Authentication error."""

    pass


class TabloConnectionError(TabloClientError):
    """Connection error."""

    pass


class TabloClient:
    """Client for communicating with Tablo devices."""

    def __init__(self, credentials: Dict[str, Any]) -> None:
        """Initialize the Tablo client with credentials."""
        self.credentials = credentials
        self.device_url = credentials.get("device", {}).get("url", "") if isinstance(credentials.get("device"), dict) else ""
        if not self.device_url:
            # Handle case where device_url is passed directly
            self.device_url = credentials.get("device_url", "")
        self.uuid = credentials.get("uuid", "")
        self.lighthouse = credentials.get("lighthouse", "")
        self.authorization = credentials.get("lighthousetv_authorization", "")
        _LOGGER.debug(
            "TabloClient initialized for device: %s (UUID: %s)",
            self.device_url,
            self.uuid[:8] + "..." if self.uuid else "None",
        )

    def _make_device_auth(
        self, method: str, path: str, body: str = "", date: str = ""
    ) -> str:
        """Generate device authentication header."""
        # MD5 hash of body if POST
        if body:
            body_hash = hashlib.md5(body.encode()).hexdigest().lower()
        else:
            body_hash = ""

        # Create signature string
        full_str = f"{method}\n{path}\n{body_hash}\n{date}"

        # Calculate HMAC-MD5
        hmac_hash = hmac.new(
            HASH_KEY.encode(), full_str.encode(), hashlib.md5
        ).hexdigest().lower()

        # Return formatted auth header
        return f"tablo:{DEVICE_KEY}:{hmac_hash}"

    def _get_device_date(self) -> str:
        """Get RFC 1123 formatted date for device requests."""
        return datetime.utcnow().strftime("%a, %d %b %Y %H:%M:%S GMT")

    async def _request_device(
        self,
        session: ClientSession,
        method: str,
        path: str,
        body: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Make authenticated request to local device."""
        url = urljoin(self.device_url.rstrip('/') + '/', path.lstrip('/'))
        date = self._get_device_date()

        _LOGGER.debug("Making %s request to device: %s", method, url)

        headers = {
            "Connection": "keep-alive",
            "Date": date,
            "Accept": ACCEPT_HEADER,
            "User-Agent": USER_AGENT,
        }

        body_str = ""
        if method == "POST" and body:
            # Format body as JSON
            device_body = {
                "bandwidth": None,
                "extra": {
                    "limitedAdTracking": 1,
                    "deviceOSVersion": "16.6",
                    "lang": "en_US",
                    "height": 1080,
                    "deviceId": "00000000-0000-0000-0000-000000000000",
                    "width": 1920,
                    "deviceModel": "iPhone10,1",
                    "deviceMake": "Apple",
                    "deviceOS": "iOS",
                },
                "device_id": self.uuid,
                "platform": "ios",
            }
            # Merge any additional body data
            if isinstance(body, dict):
                device_body.update(body)
            body_str = json.dumps(device_body)
            # Note: tablo2plex uses form-urlencoded content type (even though body is JSON)
            headers["Content-Type"] = CONTENT_TYPE_FORM
            headers["Content-Length"] = str(len(body_str))
            if is_debug_enabled():
                _LOGGER.debug("Request body: %s", log_sensitive_data(device_body))

        # Generate device authentication
        auth_header = self._make_device_auth(method, path, body_str, date)
        headers["Authorization"] = auth_header

        if is_debug_enabled():
            sanitized_headers = headers.copy()
            sanitized_headers["Authorization"] = "tablo:***REDACTED***"
            _LOGGER.debug("Request headers: %s", sanitized_headers)

        timeout = ClientTimeout(total=DEFAULT_REQUEST_TIMEOUT)
        try:
            async with session.request(
                method, url, headers=headers, data=body_str if body_str else None, timeout=timeout
            ) as response:
                _LOGGER.debug("Device response status: %s", response.status)
                response.raise_for_status()
                result = await response.json()
                if is_debug_enabled():
                    _LOGGER.debug("Device response: %s", log_sensitive_data(result))
                return result
        except aiohttp.ClientError as err:
            _LOGGER.error("Device request failed: %s - %s", url, err)
            raise TabloConnectionError(f"Device request failed: {err}") from err

    async def _request_cloud(
        self,
        session: ClientSession,
        method: str,
        path: str,
        headers: Optional[Dict[str, str]] = None,
        body: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Make request to cloud API."""
        url = f"https://{CLOUD_API_HOST}{path}"

        _LOGGER.debug("Making %s request to cloud API: %s", method, url)

        request_headers = {
            "User-Agent": USER_AGENT,
            "Accept": ACCEPT_HEADER,
            "Content-Type": CONTENT_TYPE_JSON,
        }
        if headers:
            request_headers.update(headers)

        if is_debug_enabled():
            sanitized_headers = request_headers.copy()
            if "Authorization" in sanitized_headers:
                sanitized_headers["Authorization"] = "***REDACTED***"
            if "Lighthouse" in sanitized_headers:
                sanitized_headers["Lighthouse"] = sanitized_headers["Lighthouse"][:8] + "..."
            _LOGGER.debug("Request headers: %s", sanitized_headers)
            if body:
                try:
                    body_dict = json.loads(body) if isinstance(body, str) else body
                    _LOGGER.debug("Request body: %s", log_sensitive_data(body_dict))
                except (json.JSONDecodeError, TypeError):
                    _LOGGER.debug("Request body: %s", body[:100] + "..." if len(body) > 100 else body)

        timeout = ClientTimeout(total=DEFAULT_REQUEST_TIMEOUT)
        try:
            async with session.request(
                method, url, headers=request_headers, data=body, timeout=timeout
            ) as response:
                _LOGGER.debug("Cloud API response status: %s", response.status)
                response.raise_for_status()
                result = await response.json()
                if is_debug_enabled():
                    _LOGGER.debug("Cloud API response: %s", log_sensitive_data(result))
                return result
        except aiohttp.ClientError as err:
            _LOGGER.error("Cloud API request failed: %s - %s", url, err)
            raise TabloConnectionError(f"Cloud API request failed: {err}") from err

    @staticmethod
    async def authenticate(username: str, password: str) -> Dict[str, Any]:
        """Authenticate with Tablo account and return credentials."""
        _LOGGER.info("Starting Tablo authentication for user: %s", username)
        async with ClientSession() as session:
            # Step 1: Login
            _LOGGER.debug("Step 1: Authenticating with Tablo cloud API")
            login_body = json.dumps({"email": username, "password": "***REDACTED***"})
            try:
                login_response = await TabloClient._request_cloud_static(
                    session, "POST", LOGIN_PATH, body=json.dumps({"email": username, "password": password})
                )
                _LOGGER.debug("Login response received")
            except TabloConnectionError as err:
                _LOGGER.error("Login failed: %s", err)
                raise TabloAuthenticationError(f"Login failed: {err}") from err

            if login_response.get("code") is not None:
                error_msg = login_response.get("message", "Invalid credentials")
                _LOGGER.error("Authentication failed: %s", error_msg)
                raise TabloAuthenticationError(error_msg)

            if not login_response.get("access_token") or not login_response.get(
                "token_type"
            ):
                _LOGGER.error("Invalid login response: missing access_token or token_type")
                raise TabloAuthenticationError("Invalid login response")

            authorization = f'{login_response["token_type"]} {login_response["access_token"]}'
            _LOGGER.info("Authentication successful, token received")

            # Step 2: Get account info
            _LOGGER.debug("Step 2: Fetching account information")
            account_headers = {"Authorization": authorization}
            try:
                account_response = await TabloClient._request_cloud_static(
                    session, "GET", ACCOUNT_PATH, headers=account_headers
                )
                _LOGGER.debug("Account info received")
            except TabloConnectionError as err:
                _LOGGER.error("Account fetch failed: %s", err)
                raise TabloAuthenticationError(f"Account fetch failed: {err}") from err

            if account_response.get("code") is not None:
                error_msg = account_response.get("message", "Failed to get account info")
                _LOGGER.error("Account fetch error: %s", error_msg)
                raise TabloAuthenticationError(error_msg)

            # Select profile (use first if only one)
            profiles = account_response.get("profiles", [])
            if not profiles:
                _LOGGER.error("No profiles found in account")
                raise TabloAuthenticationError("No profiles found")

            profile = profiles[0]  # Use first profile
            _LOGGER.info("Selected profile: %s (ID: %s)", profile.get("name"), profile.get("identifier"))

            # Select device (use first if only one)
            devices = account_response.get("devices", [])
            if not devices:
                _LOGGER.error("No devices found in account")
                raise TabloAuthenticationError("No devices found")

            device = devices[0]  # Use first device
            _LOGGER.info(
                "Selected device: %s (Server ID: %s) at %s",
                device.get("name"),
                device.get("serverId"),
                device.get("url"),
            )

            # Step 3: Get Lighthouse token
            _LOGGER.debug("Step 3: Selecting profile and device to get Lighthouse token")
            select_body = json.dumps(
                {"pid": profile["identifier"], "sid": device["serverId"]}
            )
            try:
                select_response = await TabloClient._request_cloud_static(
                    session,
                    "POST",
                    ACCOUNT_SELECT_PATH,
                    headers=account_headers,
                    body=select_body,
                )
                _LOGGER.debug("Device selection response received")
            except TabloConnectionError as err:
                _LOGGER.error("Device selection failed: %s", err)
                raise TabloAuthenticationError(f"Device selection failed: {err}") from err

            lighthouse = select_response.get("token")
            if not lighthouse:
                _LOGGER.error("Failed to get Lighthouse token from response")
                raise TabloAuthenticationError("Failed to get Lighthouse token")

            _LOGGER.info("Lighthouse token obtained")
            # Step 4: Generate UUID
            device_uuid = str(uuid.uuid4())
            _LOGGER.debug("Generated device UUID: %s", device_uuid)

            # Step 5: Optionally verify device connection (skip if unreachable)
            _LOGGER.debug("Step 5: Optionally verifying connection to local device")
            device_url = device.get("url", "")
            if not device_url:
                _LOGGER.warning("Device URL not found in device info, using default tuner count")
                tuners = 2  # Default tuner count
                device_model = device.get("name", "Unknown")
            else:
                # Try to verify device connection, but don't fail setup if it doesn't work
                temp_credentials = {
                    "device": device,
                    "uuid": device_uuid,
                    "lighthouse": lighthouse,
                    "lighthousetv_authorization": authorization,
                    "lighthousetv_identifier": account_response.get("identifier", ""),
                }
                temp_client = TabloClient(temp_credentials)

                try:
                    _LOGGER.debug("Attempting to connect to device at %s (optional verification)", device_url)
                    server_info = await temp_client.get_server_info()
                    tuners = server_info.get("model", {}).get("tuners", 2)
                    device_model = server_info.get("model", {}).get("name", "Unknown")
                    _LOGGER.info(
                        "Device verified: %s with %d tuner(s)",
                        device_model,
                        tuners,
                    )
                except TabloConnectionError as err:
                    _LOGGER.warning(
                        "Could not connect to device at %s during setup (this is OK): %s. "
                        "Using default tuner count (2). Device connection will be attempted when needed.",
                        device_url,
                        err
                    )
                    tuners = 2  # Default tuner count (matches tablo2plex default)
                    device_model = device.get("name", "Unknown")

            # Return complete credentials
            _LOGGER.info("Authentication completed successfully")
            credentials = {
                "lighthousetv_authorization": authorization,
                "lighthousetv_identifier": account_response.get("identifier", ""),
                "profile": profile,
                "device": device,
                "lighthouse": lighthouse,
                "uuid": device_uuid,
                "tuners": tuners,
            }
            if is_debug_enabled():
                _LOGGER.debug("Credentials structure: %s", log_sensitive_data(credentials))
            return credentials

    @staticmethod
    async def _request_cloud_static(
        session: ClientSession,
        method: str,
        path: str,
        headers: Optional[Dict[str, str]] = None,
        body: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Static method to make cloud API requests."""
        url = f"https://{CLOUD_API_HOST}{path}"

        if is_debug_enabled():
            _LOGGER.debug("Cloud API request: %s %s", method, url)

        request_headers = {
            "User-Agent": USER_AGENT,
            "Accept": ACCEPT_HEADER,
            "Content-Type": CONTENT_TYPE_JSON,
        }
        if headers:
            request_headers.update(headers)

        if is_debug_enabled():
            sanitized_headers = request_headers.copy()
            if "Authorization" in sanitized_headers:
                sanitized_headers["Authorization"] = "***REDACTED***"
            _LOGGER.debug("Request headers: %s", sanitized_headers)

        timeout = ClientTimeout(total=DEFAULT_REQUEST_TIMEOUT)
        try:
            async with session.request(
                method, url, headers=request_headers, data=body, timeout=timeout
            ) as response:
                if is_debug_enabled():
                    _LOGGER.debug("Response status: %s", response.status)
                response.raise_for_status()
                result = await response.json()
                return result
        except aiohttp.ClientError as err:
            _LOGGER.error("Cloud API request failed: %s - %s", url, err)
            raise TabloConnectionError(f"Cloud API request failed: {err}") from err

    async def get_server_info(self) -> Dict[str, Any]:
        """Get server information from local device."""
        _LOGGER.debug("Getting server info from device")
        connector = TCPConnector(ssl=False)  # Explicitly disable SSL for HTTP device connections
        timeout = ClientTimeout(total=DEFAULT_REQUEST_TIMEOUT)
        async with ClientSession(connector=connector, timeout=timeout) as session:
            return await self._request_device(session, "GET", SERVER_INFO_PATH)

    async def get_channels(self) -> List[Dict[str, Any]]:
        """Fetch channel lineup from cloud API."""
        _LOGGER.debug("Fetching channel lineup from cloud API")
        path = CHANNELS_PATH.format(lighthouse=self.lighthouse)
        headers = {
            "Authorization": self.authorization,
            "Lighthouse": self.lighthouse,
        }

        async with ClientSession() as session:
            response = await self._request_cloud(session, "GET", path, headers=headers)
            if isinstance(response, list):
                _LOGGER.info("Retrieved %d channels from cloud API", len(response))
                return response
            _LOGGER.warning("Unexpected response format from channels API: %s", type(response))
            return []

    async def watch_channel(self, channel_id: str) -> Dict[str, Any]:
        """Set channel on device (initiates stream)."""
        _LOGGER.info("Setting channel on device: %s", channel_id)
        path = WATCH_CHANNEL_PATH.format(channel_id=channel_id)

        connector = TCPConnector(ssl=False)  # Explicitly disable SSL for HTTP device connections
        timeout = ClientTimeout(total=DEFAULT_REQUEST_TIMEOUT)
        async with ClientSession(connector=connector, timeout=timeout) as session:
            result = await self._request_device(session, "POST", path, body={})
            _LOGGER.info("Channel watch request completed for channel: %s", channel_id)
            return result

