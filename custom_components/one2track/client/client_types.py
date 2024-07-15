from typing import NamedTuple, TypedDict


class AuthenticationError(Exception):
    """This error is thrown when Authentication fails, which can mean the username/password or domain is incorrect"""

    pass


class One2TrackConfig(NamedTuple):
    """
    This is our config for logging into One2Track

    """

    username: str
    password: str
    id: str = None


class TrackerStatus(TypedDict):
    """
    Returned by the API
    """

    name: str
    phoneNumber: str
    lastUpdate: int
    lat: float
    long: float


class Location(TypedDict):
    id: int
    last_communication: str  # json date
    last_location_update: str  # json date
    address: str
    latitude: float
    longitude: float
    altitude: float
    location_type: str  # e.g. WIFI
    signal_strength: int
    satellite_count: int
    speed: float
    battery_percentage: int
    host: str
    port: int


class Simcard(TypedDict):
    balance_cents: float
    tariff_type: str


class TrackerDevice(TypedDict):
    id: int
    serial_number: str
    name: str
    phone_number: str
    status: str
    uuid: str
    last_location: Location
    simcard: Simcard
