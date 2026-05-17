"""Tests for authentication and cookie/CSRF parsing."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.one2track.client.client_types import (
    AuthenticationError,
    One2TrackConfig,
)
from custom_components.one2track.client.gps_client import GpsClient


class TestParseCsrf:
    def test_extracts_token(self):
        html = '<meta name="csrf-token" content="abc123XYZ+/==" />'
        assert GpsClient._parse_csrf(html) == "abc123XYZ+/=="

    def test_extracts_token_with_whitespace_variations(self):
        html = '<meta name="csrf-token"  content="token123">'
        assert GpsClient._parse_csrf(html) == "token123"

    def test_raises_on_missing_token(self):
        with pytest.raises(AuthenticationError, match="CSRF token not found"):
            GpsClient._parse_csrf("<html><body>no token here</body></html>")

    def test_raises_on_empty_html(self):
        with pytest.raises(AuthenticationError, match="CSRF token not found"):
            GpsClient._parse_csrf("")


class TestExtractCookie:
    def _make_response(self, set_cookie_headers: list[str]):
        response = MagicMock()
        response.headers = MagicMock()
        response.headers.getall = MagicMock(return_value=set_cookie_headers)
        return response

    def test_extracts_from_set_cookie(self):
        resp = self._make_response(["_iadmin=abc123; path=/; HttpOnly; SameSite=Lax"])
        assert GpsClient._extract_cookie(resp) == "abc123"

    def test_extracts_from_multiple_set_cookie_headers(self):
        resp = self._make_response(
            [
                "accepted_cookies=true; path=/",
                "_iadmin=session_value; path=/; HttpOnly",
            ]
        )
        assert GpsClient._extract_cookie(resp) == "session_value"

    def test_returns_empty_when_no_session_cookie(self):
        resp = self._make_response(["other_cookie=val; path=/"])
        assert GpsClient._extract_cookie(resp) == ""

    def test_returns_empty_when_no_headers(self):
        resp = self._make_response([])
        assert GpsClient._extract_cookie(resp) == ""

    def test_ignores_empty_cookie_value(self):
        resp = self._make_response(["_iadmin=; path=/; HttpOnly"])
        assert GpsClient._extract_cookie(resp) == ""


class TestLoginFlow:
    @pytest.mark.asyncio
    async def test_install_sets_account_id(self):
        config = One2TrackConfig(username="user", password="pass")
        session = AsyncMock()

        csrf_response = MagicMock()
        csrf_response.status = 200
        csrf_response.text = AsyncMock(return_value='<meta name="csrf-token" content="csrf123" />')
        csrf_response.headers = MagicMock()
        csrf_response.headers.getall = MagicMock(
            return_value=["_iadmin=session1; path=/; HttpOnly"]
        )

        login_response = MagicMock()
        login_response.status = 302
        login_response.headers = MagicMock()
        login_response.headers.getall = MagicMock(
            return_value=["_iadmin=session2; path=/; HttpOnly"]
        )

        redirect_response = MagicMock()
        redirect_response.status = 302
        redirect_response.headers = {
            "Location": "https://www.one2trackgps.com/users/myaccount/devices"
        }

        session.get = AsyncMock(side_effect=[csrf_response, redirect_response])
        session.post = AsyncMock(return_value=login_response)

        client = GpsClient(config, session)
        account_id = await client.install()

        assert account_id == "myaccount"
        assert client.account_id == "myaccount"
        assert client._cookie == "session2"

    @pytest.mark.asyncio
    async def test_login_raises_on_non_302(self):
        config = One2TrackConfig(username="user", password="wrong")
        session = AsyncMock()

        csrf_response = MagicMock()
        csrf_response.status = 200
        csrf_response.text = AsyncMock(return_value='<meta name="csrf-token" content="csrf123" />')
        csrf_response.headers = MagicMock()
        csrf_response.headers.getall = MagicMock(return_value=["_iadmin=sess; path=/"])

        login_response = MagicMock()
        login_response.status = 200
        login_response.headers = MagicMock()
        login_response.headers.getall = MagicMock(return_value=[])

        session.get = AsyncMock(return_value=csrf_response)
        session.post = AsyncMock(return_value=login_response)

        client = GpsClient(config, session)

        with pytest.raises(AuthenticationError, match="Invalid username"):
            await client.install()


class TestRequestCookieHeader:
    @pytest.mark.asyncio
    async def test_sends_cookie_via_header_not_kwarg(self):
        config = One2TrackConfig(username="user", password="pass", id="acc")
        session = AsyncMock()

        response = MagicMock()
        response.status = 200
        response.json = AsyncMock(return_value=[])
        session.get = AsyncMock(return_value=response)

        client = GpsClient(config, session)
        client._cookie = "my_session_token"

        await client._get_device_data()

        call_args = session.get.call_args
        headers = call_args[1]["headers"]
        assert "Cookie" in headers
        assert "_iadmin=my_session_token" in headers["Cookie"]
        assert "accepted_cookies=true" in headers["Cookie"]
        # No cookies= kwarg should be passed
        assert "cookies" not in call_args[1]
