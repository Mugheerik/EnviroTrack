import logging

from envirotrack.config import PRIMARY_LOCATION
from envirotrack.freshness import check_data_freshness

logger = logging.getLogger(__name__)


def monitor_location(location: str) -> dict:
    result = check_data_freshness(location)

    age_seconds = result["age_seconds"]

    if age_seconds is None:
        logger.error("No raw data available for %s", location)
    else:
        age_hours = age_seconds / 3600

        logger.info(
            "Location: %s | Status: %s | Data age: %.2f hours",
            location,
            result["status"],
            age_hours,
        )

    return result


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
    )

    result = monitor_location(PRIMARY_LOCATION.name)

    if result["status"] != "fresh":
        raise SystemExit(1)
