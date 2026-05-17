import logging
import re
from http.cookies import SimpleCookie

from aiohttp import ClientSession

from .client_types import AuthenticationError, One2TrackConfig, TrackerDevice

_LOGGER = logging.getLogger(__name__)

BASE_URL = "https://www.one2trackgps.com"
LOGIN_URL = f"{BASE_URL}/auth/users/sign_in"
DEVICE_URL = f"{BASE_URL}/users/{{account_id}}/devices"
SESSION_COOKIE = "_iadmin"


class GpsClient:
    def __init__(self, config: One2TrackConfig, session: ClientSession) -> None:
        self.config = config
        self.account_id: str = config.id or ""
        self.session = session
        self._cookie: str = ""
        self._csrf: str = ""

    async def install(self) -> str:
        await self._get_csrf()
        await self._login()
        return await self._get_user_id()

    async def update(self) -> list[TrackerDevice]:
        await self._ensure_authenticated()
        return await self._get_device_data()

    async def power_off(self, device_uuid: str) -> bool:
        """Shut down the device remotely."""
        return await self._send_function(device_uuid, "0048", "Shutdown")

    async def force_update(self, device_uuid: str) -> bool:
        """Activate positioning mode on the device for ~2 minutes."""
        return await self._send_function(device_uuid, "0039", "Actieve positioneringmodus")

    async def send_message(self, device_uuid: str, message: str) -> bool:
        """Send a text message to a One2Track device."""
        await self._ensure_authenticated()
        csrf = await self._fresh_csrf_token()

        url = f"{BASE_URL}/devices/{device_uuid}/messages"
        headers = {
            "x-csrf-token": csrf,
            "content-type": "application/x-www-form-urlencoded;charset=UTF-8",
            "accept": "text/vnd.turbo-stream.html, text/html, application/xhtml+xml",
        }
        data = {
            "utf8": "✓",
            "authenticity_token": csrf,
            "device_message[message]": message,
        }

        response = await self._request(url, data=data, extra_headers=headers)
        return response.status == 200

    # ------------------------------------------------------------------
    # Internal auth flow
    # ------------------------------------------------------------------

    async def _ensure_authenticated(self) -> None:
        if not self._cookie:
            _LOGGER.debug("No session cookie, performing login")
            await self._get_csrf()
            await self._login()
            await self._get_user_id()

    async def _get_csrf(self) -> None:
        response = await self._request(LOGIN_URL)
        if response.status != 200:
            raise AuthenticationError("Login page unavailable")

        html = await response.text()
        self._csrf = self._parse_csrf(html)
        cookie = self._extract_cookie(response)
        if cookie:
            self._cookie = cookie

    async def _login(self) -> None:
        login_data = {
            "authenticity_token": self._csrf,
            "user[login]": self.config.username,
            "user[password]": self.config.password,
            "gdpr": "1",
            "user[remember_me]": "1",
        }
        response = await self._request(LOGIN_URL, data=login_data, allow_redirects=False)

        if response.status == 302:
            new_cookie = self._extract_cookie(response)
            if new_cookie:
                self._cookie = new_cookie
                return

        raise AuthenticationError("Invalid username or password")

    async def _get_user_id(self) -> str:
        response = await self._request(f"{BASE_URL}/", allow_redirects=False)
        if response.status != 302 or "Location" not in response.headers:
            raise AuthenticationError("Could not determine account ID")

        location = response.headers["Location"]
        self.account_id = location.split("/")[4]
        return self.account_id

    async def _fresh_csrf_token(self) -> str:
        """Fetch a fresh CSRF token (needed before each action request)."""
        response = await self._request(LOGIN_URL)
        if response.status != 200:
            raise AuthenticationError("Could not get CSRF token")

        html = await response.text()
        new_cookie = self._extract_cookie(response)
        if new_cookie:
            self._cookie = new_cookie
        return self._parse_csrf(html)

    async def _send_function(self, device_uuid: str, code: str, name: str) -> bool:
        """Send a function command to a device."""
        await self._ensure_authenticated()
        csrf = await self._fresh_csrf_token()

        url = f"{BASE_URL}/api/devices/{device_uuid}/functions"
        headers = {
            "x-csrf-token": csrf,
            "x-requested-with": "XMLHttpRequest",
            "content-type": "application/x-www-form-urlencoded; charset=UTF-8",
        }
        data = {
            "utf8": "✓",
            "function[code]": code,
            "function[name]": name,
        }

        response = await self._request(url, data=data, extra_headers=headers)
        return response.status == 200

    async def _get_device_data(self) -> list[TrackerDevice]:
        url = DEVICE_URL.format(account_id=self.account_id)
        response = await self._request(url, use_json=True)

        if response.status != 200:
            _LOGGER.error("Cannot get devices, status %s", response.status)
            self._cookie = ""
            self._csrf = ""
            raise AuthenticationError(f"API returned status {response.status}")

        data = await response.json(content_type=None)
        _LOGGER.debug("Got %s devices", len(data))
        return [item["device"] for item in data]

    # ------------------------------------------------------------------
    # HTTP helper — sends cookies via raw header to avoid session jar issues
    # ------------------------------------------------------------------

    async def _request(
        self,
        url: str,
        *,
        data: dict | None = None,
        allow_redirects: bool = True,
        use_json: bool = False,
        extra_headers: dict | None = None,
    ):
        headers: dict[str, str] = {}

        if data is not None:
            headers["content-type"] = "application/x-www-form-urlencoded"
        if use_json:
            headers["content-type"] = "application/json"
            headers["Accept"] = "application/json"
        if extra_headers:
            headers.update(extra_headers)

        # Build cookie header manually so the session's cookie jar
        # never interferes with our authentication state.
        cookie_parts = ["accepted_cookies=true"]
        if self._cookie:
            cookie_parts.append(f"{SESSION_COOKIE}={self._cookie}")
        headers["Cookie"] = "; ".join(cookie_parts)

        _LOGGER.debug("[http] %s", url)

        if data is not None:
            return await self.session.post(
                url, data=data, headers=headers, allow_redirects=allow_redirects
            )
        return await self.session.get(url, headers=headers, allow_redirects=allow_redirects)

    # ------------------------------------------------------------------
    # Parsing helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_cookie(response) -> str:
        """Extract the session cookie from a response's Set-Cookie headers."""
        for header_value in response.headers.getall("Set-Cookie", []):
            sc = SimpleCookie()
            sc.load(header_value)
            if SESSION_COOKIE in sc and sc[SESSION_COOKIE].value:
                return sc[SESSION_COOKIE].value
        return ""

    @staticmethod
    def _parse_csrf(html: str) -> str:
        """Extract the CSRF token from a login page's HTML."""
        m = re.search(r'name="csrf-token"\s+content="([^"]+)"', html)
        if not m:
            raise AuthenticationError("CSRF token not found on page")
        return m.group(1)
