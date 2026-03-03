from typing import NamedTuple, TypedDict


class AuthenticationError(Exception):
    """Raised when authentication fails (wrong username/password or unavailable)."""


class One2TrackConfig(NamedTuple):
    """Login configuration for One2Track."""

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
    last_communication: str
    last_location_update: str
    address: str
    latitude: str
    longitude: str
    altitude: str
    location_type: str
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
    status: str
    uuid: str
    last_location: Location
    simcard: Simcard
