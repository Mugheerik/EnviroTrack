from datetime import UTC, datetime, timedelta

from envirotrack.db import fetch_latest_collection_time

DEFAULT_MAX_AGE = timedelta(hours=6)


def check_data_freshness(
    location: str,
    max_age: timedelta = DEFAULT_MAX_AGE,
    now: datetime | None = None,
) -> dict:
    collected_at = fetch_latest_collection_time(location)

    if collected_at is None:
        return {
            "location": location,
            "status": "missing",
            "collected_at": None,
            "age_seconds": None,
        }

    current_time = now or datetime.now(UTC)
    age = current_time - collected_at

    if age < timedelta(0):
        status = "future_timestamp"
    elif age > max_age:
        status = "stale"
    else:
        status = "fresh"

    return {
        "location": location,
        "status": status,
        "collected_at": collected_at,
        "age_seconds": age.total_seconds(),
    }
