"""Tests distinguishing confirmed auth failures from transient/site errors.

These make sure a temporary One2Track outage (5xx/429) is never mistaken for
bad credentials, and that a confirmed credential rejection (401/403, or a
login form re-render) still forces a fresh login next time.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.one2track.client.client_types import (
    AuthenticationError,
    One2TrackConfig,
    SiteUnavailableError,
)
from custom_components.one2track.client.gps_client import GpsClient


def _response(status: int, *, headers=None, set_cookie=None):
    resp = MagicMock()
    resp.status = status
    resp.headers = headers if headers is not None else MagicMock()
    if set_cookie is not None and not isinstance(resp.headers, dict):
        resp.headers.getall = MagicMock(return_value=set_cookie)
    return resp


class TestGetCsrfClassification:
    @pytest.mark.asyncio
    async def test_non_200_is_site_unavailable_not_auth_error(self):
        config = One2TrackConfig(username="user", password="pass")
        session = AsyncMock()
        session.get = AsyncMock(return_value=_response(503))

        client = GpsClient(config, session)
        with pytest.raises(SiteUnavailableError):
            await client._get_csrf()


class TestLoginClassification:
    @pytest.mark.asyncio
    async def test_5xx_is_site_unavailable(self):
        config = One2TrackConfig(username="user", password="pass")
        session = AsyncMock()
        session.post = AsyncMock(return_value=_response(503, set_cookie=[]))

        client = GpsClient(config, session)
        client._csrf = "tok"
        with pytest.raises(SiteUnavailableError):
            await client._login()

    @pytest.mark.asyncio
    async def test_form_rerender_is_auth_error(self):
        config = One2TrackConfig(username="user", password="wrong")
        session = AsyncMock()
        session.post = AsyncMock(return_value=_response(200, set_cookie=[]))

        client = GpsClient(config, session)
        client._csrf = "tok"
        with pytest.raises(AuthenticationError, match="Invalid username"):
            await client._login()


class TestGetUserIdClassification:
    @pytest.mark.asyncio
    async def test_5xx_is_site_unavailable(self):
        config = One2TrackConfig(username="user", password="pass")
        session = AsyncMock()
        session.get = AsyncMock(return_value=_response(503, headers={}))

        client = GpsClient(config, session)
        with pytest.raises(SiteUnavailableError):
            await client._get_user_id()

    @pytest.mark.asyncio
    async def test_missing_redirect_is_auth_error(self):
        config = One2TrackConfig(username="user", password="pass")
        session = AsyncMock()
        session.get = AsyncMock(return_value=_response(200, headers={}))

        client = GpsClient(config, session)
        with pytest.raises(AuthenticationError, match="Could not determine account ID"):
            await client._get_user_id()


class TestGetDeviceDataClassification:
    @pytest.mark.asyncio
    async def test_503_is_site_unavailable_and_keeps_session(self):
        config = One2TrackConfig(username="user", password="pass", id="acc")
        session = AsyncMock()
        session.get = AsyncMock(return_value=_response(503))

        client = GpsClient(config, session)
        client._cookie = "still_valid_cookie"
        client._csrf = "still_valid_csrf"

        with pytest.raises(SiteUnavailableError):
            await client._get_device_data()

        # A transient server error must not force a full re-login next cycle.
        assert client._cookie == "still_valid_cookie"
        assert client._csrf == "still_valid_csrf"

    @pytest.mark.asyncio
    async def test_401_is_auth_error_and_clears_session(self):
        config = One2TrackConfig(username="user", password="pass", id="acc")
        session = AsyncMock()
        session.get = AsyncMock(return_value=_response(401))

        client = GpsClient(config, session)
        client._cookie = "rejected_cookie"
        client._csrf = "rejected_csrf"

        with pytest.raises(AuthenticationError):
            await client._get_device_data()

        # A confirmed rejection must force a fresh login next cycle.
        assert client._cookie == ""
        assert client._csrf == ""

    @pytest.mark.asyncio
    async def test_403_is_auth_error_and_clears_session(self):
        config = One2TrackConfig(username="user", password="pass", id="acc")
        session = AsyncMock()
        session.get = AsyncMock(return_value=_response(403))

        client = GpsClient(config, session)
        client._cookie = "rejected_cookie"

        with pytest.raises(AuthenticationError):
            await client._get_device_data()

        assert client._cookie == ""
