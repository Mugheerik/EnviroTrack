import json
import logging
from datetime import UTC, datetime
from pathlib import Path

from envirotrack.client import fetch_weather
from envirotrack.config import PRIMARY_LOCATION
from envirotrack.db import (
    complete_pipeline_run,
    create_pipeline_run,
    fail_pipeline_run,
    insert_raw_weather,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
RAW_DATA_DIR = PROJECT_ROOT / "data" / "raw"

logger = logging.getLogger(__name__)


def ingest_weather() -> Path:
    location = PRIMARY_LOCATION

    logger.info("Starting ingestion for %s", location.name)

    run_id = create_pipeline_run(
        pipeline_name="weather_ingestion",
        location=location.name,
    )

    try:
        collected_at = datetime.now(UTC)

        payload = fetch_weather(
            location.latitude,
            location.longitude,
        )

        RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)

        timestamp = collected_at.strftime("%Y%m%dT%H%M%S%fZ")
        filename = f"weather_{location.name}_{timestamp}.json"
        file_path = RAW_DATA_DIR / filename

        with file_path.open("w", encoding="utf-8") as file:
            json.dump(payload, file, indent=4, ensure_ascii=False)

        logger.info("Raw file persisted: %s", file_path)

        insert_raw_weather(
            payload=payload,
            location=location.name,
            requested_latitude=location.latitude,
            requested_longitude=location.longitude,
            collected_at=collected_at,
        )

        complete_pipeline_run(
            run_id=run_id,
            records_processed=1,
        )

        logger.info(
            "Ingestion completed successfully. Run ID: %s",
            run_id,
        )

        return file_path

    except Exception as error:
        logger.exception(
            "Ingestion failed. Run ID: %s",
            run_id,
        )

        try:
            fail_pipeline_run(run_id, str(error))
        except Exception:
            logger.exception(
                "Could not update failed ingestion run %s",
                run_id,
            )

        raise


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
    )

    ingest_weather()
