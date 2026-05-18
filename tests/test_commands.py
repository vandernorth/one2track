"""Tests for device command services (power_off, force_update)."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.one2track.client.client_types import One2TrackConfig
from custom_components.one2track.client.gps_client import GpsClient


class TestSendFunction:
    @pytest.fixture
    def client(self):
        config = One2TrackConfig(username="user", password="pass", id="test_id")
        session = AsyncMock()
        c = GpsClient(config, session)
        c._cookie = "existing_session"
        return c

    @pytest.mark.asyncio
    async def test_power_off_sends_correct_code(self, client):
        mock_csrf_response = MagicMock()
        mock_csrf_response.status = 200
        mock_csrf_response.text = AsyncMock(
            return_value='<meta name="csrf-token" content="csrf_tok" />'
        )
        mock_csrf_response.headers = MagicMock()
        mock_csrf_response.headers.getall = MagicMock(return_value=[])

        mock_func_response = MagicMock()
        mock_func_response.status = 200

        client.session.get = AsyncMock(return_value=mock_csrf_response)
        client.session.post = AsyncMock(return_value=mock_func_response)

        result = await client.power_off("device-uuid-123")

        assert result is True
        call_args = client.session.post.call_args
        assert "api/devices/device-uuid-123/functions" in call_args[0][0]
        post_data = call_args[1]["data"]
        assert post_data["function[code]"] == "0048"
        assert post_data["function[name]"] == "Shutdown"

    @pytest.mark.asyncio
    async def test_force_update_sends_correct_code(self, client):
        mock_csrf_response = MagicMock()
        mock_csrf_response.status = 200
        mock_csrf_response.text = AsyncMock(
            return_value='<meta name="csrf-token" content="csrf_tok" />'
        )
        mock_csrf_response.headers = MagicMock()
        mock_csrf_response.headers.getall = MagicMock(return_value=[])

        mock_func_response = MagicMock()
        mock_func_response.status = 200

        client.session.get = AsyncMock(return_value=mock_csrf_response)
        client.session.post = AsyncMock(return_value=mock_func_response)

        result = await client.force_update("device-uuid-456")

        assert result is True
        call_args = client.session.post.call_args
        assert "api/devices/device-uuid-456/functions" in call_args[0][0]
        post_data = call_args[1]["data"]
        assert post_data["function[code]"] == "0039"
        assert post_data["function[name]"] == "Actieve positioneringmodus"

    @pytest.mark.asyncio
    async def test_returns_false_on_non_200(self, client):
        mock_csrf_response = MagicMock()
        mock_csrf_response.status = 200
        mock_csrf_response.text = AsyncMock(return_value='<meta name="csrf-token" content="tok" />')
        mock_csrf_response.headers = MagicMock()
        mock_csrf_response.headers.getall = MagicMock(return_value=[])

        mock_func_response = MagicMock()
        mock_func_response.status = 422

        client.session.get = AsyncMock(return_value=mock_csrf_response)
        client.session.post = AsyncMock(return_value=mock_func_response)

        result = await client.power_off("device-uuid")
        assert result is False
