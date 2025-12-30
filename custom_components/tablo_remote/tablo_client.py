"""Tablo API client for communicating with Tablo devices."""
import asyncio
import hashlib
import hmac
import json
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

import aiohttp
from aiohttp import ClientSession, ClientTimeout

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
        self.device_url = credentials.get("device", {}).get("url", "")
        self.uuid = credentials.get("uuid", "")
        self.lighthouse = credentials.get("lighthouse", "")
        self.authorization = credentials.get("lighthousetv_authorization", "")

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
        url = f"{self.device_url}{path}"
        date = self._get_device_date()

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
            # Note: Source code uses form-urlencoded but sends JSON. Using JSON for correctness.
            headers["Content-Type"] = CONTENT_TYPE_JSON
            headers["Content-Length"] = str(len(body_str))

        # Generate device authentication
        auth_header = self._make_device_auth(method, path, body_str, date)
        headers["Authorization"] = auth_header

        timeout = ClientTimeout(total=DEFAULT_REQUEST_TIMEOUT)
        try:
            async with session.request(
                method, url, headers=headers, data=body_str if body_str else None, timeout=timeout
            ) as response:
                response.raise_for_status()
                return await response.json()
        except aiohttp.ClientError as err:
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

        request_headers = {
            "User-Agent": USER_AGENT,
            "Accept": ACCEPT_HEADER,
            "Content-Type": CONTENT_TYPE_JSON,
        }
        if headers:
            request_headers.update(headers)

        timeout = ClientTimeout(total=DEFAULT_REQUEST_TIMEOUT)
        try:
            async with session.request(
                method, url, headers=request_headers, data=body, timeout=timeout
            ) as response:
                response.raise_for_status()
                return await response.json()
        except aiohttp.ClientError as err:
            raise TabloConnectionError(f"Cloud API request failed: {err}") from err

    @staticmethod
    async def authenticate(username: str, password: str) -> Dict[str, Any]:
        """Authenticate with Tablo account and return credentials."""
        async with ClientSession() as session:
            # Step 1: Login
            login_body = json.dumps({"email": username, "password": password})
            try:
                login_response = await TabloClient._request_cloud_static(
                    session, "POST", LOGIN_PATH, body=login_body
                )
            except TabloConnectionError as err:
                raise TabloAuthenticationError(f"Login failed: {err}") from err

            if login_response.get("code") is not None:
                raise TabloAuthenticationError(
                    login_response.get("message", "Invalid credentials")
                )

            if not login_response.get("access_token") or not login_response.get(
                "token_type"
            ):
                raise TabloAuthenticationError("Invalid login response")

            authorization = f'{login_response["token_type"]} {login_response["access_token"]}'

            # Step 2: Get account info
            account_headers = {"Authorization": authorization}
            try:
                account_response = await TabloClient._request_cloud_static(
                    session, "GET", ACCOUNT_PATH, headers=account_headers
                )
            except TabloConnectionError as err:
                raise TabloAuthenticationError(f"Account fetch failed: {err}") from err

            if account_response.get("code") is not None:
                raise TabloAuthenticationError(
                    account_response.get("message", "Failed to get account info")
                )

            # Select profile (use first if only one)
            profiles = account_response.get("profiles", [])
            if not profiles:
                raise TabloAuthenticationError("No profiles found")

            profile = profiles[0]  # Use first profile

            # Select device (use first if only one)
            devices = account_response.get("devices", [])
            if not devices:
                raise TabloAuthenticationError("No devices found")

            device = devices[0]  # Use first device

            # Step 3: Get Lighthouse token
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
            except TabloConnectionError as err:
                raise TabloAuthenticationError(f"Device selection failed: {err}") from err

            lighthouse = select_response.get("token")
            if not lighthouse:
                raise TabloAuthenticationError("Failed to get Lighthouse token")

            # Step 4: Generate UUID
            device_uuid = str(uuid.uuid4())

            # Step 5: Verify device connection
            device_url = device.get("url", "")
            if not device_url:
                raise TabloAuthenticationError("Device URL not found")

            # Create temporary client to verify device
            temp_credentials = {
                "device": device,
                "uuid": device_uuid,
                "lighthouse": lighthouse,
                "lighthousetv_authorization": authorization,
                "lighthousetv_identifier": account_response.get("identifier", ""),
            }
            temp_client = TabloClient(temp_credentials)

            try:
                server_info = await temp_client.get_server_info()
            except TabloConnectionError as err:
                raise TabloConnectionError(
                    f"Could not connect to device at {device_url}: {err}"
                ) from err

            tuners = server_info.get("model", {}).get("tuners", 2)

            # Return complete credentials
            return {
                "lighthousetv_authorization": authorization,
                "lighthousetv_identifier": account_response.get("identifier", ""),
                "profile": profile,
                "device": device,
                "lighthouse": lighthouse,
                "uuid": device_uuid,
                "tuners": tuners,
            }

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

        request_headers = {
            "User-Agent": USER_AGENT,
            "Accept": ACCEPT_HEADER,
            "Content-Type": CONTENT_TYPE_JSON,
        }
        if headers:
            request_headers.update(headers)

        timeout = ClientTimeout(total=DEFAULT_REQUEST_TIMEOUT)
        try:
            async with session.request(
                method, url, headers=request_headers, data=body, timeout=timeout
            ) as response:
                response.raise_for_status()
                return await response.json()
        except aiohttp.ClientError as err:
            raise TabloConnectionError(f"Cloud API request failed: {err}") from err

    async def get_server_info(self) -> Dict[str, Any]:
        """Get server information from local device."""
        async with ClientSession() as session:
            return await self._request_device(session, "GET", SERVER_INFO_PATH)

    async def get_channels(self) -> List[Dict[str, Any]]:
        """Fetch channel lineup from cloud API."""
        path = CHANNELS_PATH.format(lighthouse=self.lighthouse)
        headers = {
            "Authorization": self.authorization,
            "Lighthouse": self.lighthouse,
        }

        async with ClientSession() as session:
            response = await self._request_cloud(session, "GET", path, headers=headers)
            if isinstance(response, list):
                return response
            return []

    async def watch_channel(self, channel_id: str) -> Dict[str, Any]:
        """Set channel on device (initiates stream)."""
        path = WATCH_CHANNEL_PATH.format(channel_id=channel_id)

        async with ClientSession() as session:
            return await self._request_device(session, "POST", path, body={})

