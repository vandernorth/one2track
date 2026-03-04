from typing import NamedTuple, TypedDict


class AuthenticationError(Exception):
    """This error is thrown when Authentication fails, which can mean the username/password or domain is incorrect"""


class One2TrackConfig(NamedTuple):
    """
    This is our config for logging into One2Track

    """

    username: str
    password: str
    id: str | None = None


class Station(TypedDict):
    strength: str
    mnc: str
    mcc: str
    lac: str
    cid: str


class Router(TypedDict):
    signalStrength: str
    name: str
    macAddress: str


class MetaData(TypedDict, total=False):
    tumble: str
    steps: str
    stations: list[Station]
    routers: list[Router]
    course: float
    accuracy_meters: float
    accuracy: str


class Location(TypedDict):
    id: int
    last_communication: str  # json date
    last_location_update: str  # json date
    address: str
    latitude: str
    longitude: str
    altitude: str
    location_type: str  # e.g. WIFI
    signal_strength: int
    satellite_count: int
    speed: str
    battery_percentage: int
    meta_data: MetaData
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
    status: str  # e.g. GPS, WIFI
    uuid: str
    last_location: Location
    simcard: Simcard
