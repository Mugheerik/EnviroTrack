from dataclasses import dataclass


@dataclass(frozen=True)
class Location:
    name: str
    latitude: float
    longitude: float


PRIMARY_LOCATION = Location(
    name="abbottabad",
    latitude=34.1688,
    longitude=73.2215,
)

TIMEZONE = "Asia/Karachi"
