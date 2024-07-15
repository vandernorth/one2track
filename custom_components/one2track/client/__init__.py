from .gps_client import GpsClient
from .client_types import One2TrackConfig, AuthenticationError, TrackerDevice


def get_client(config: One2TrackConfig) -> GpsClient:
    return GpsClient(config)
