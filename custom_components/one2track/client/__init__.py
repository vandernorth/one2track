from aiohttp import ClientSession, DummyCookieJar

from .client_types import AuthenticationError as AuthenticationError
from .client_types import One2TrackConfig as One2TrackConfig
from .client_types import TrackerDevice as TrackerDevice
from .gps_client import GpsClient as GpsClient


def get_client(config: One2TrackConfig, session: ClientSession | None = None) -> GpsClient:
    if session is None:
        session = ClientSession(cookie_jar=DummyCookieJar())
    return GpsClient(config, session)
