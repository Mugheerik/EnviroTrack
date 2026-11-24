import logging

from envirotrack.config import PRIMARY_LOCATION
from envirotrack.ingestion import ingest_weather
from envirotrack.monitoring import monitor_location
from envirotrack.processing import process_latest_weather

logger = logging.getLogger(__name__)


def run_pipeline() -> dict:
    location = PRIMARY_LOCATION.name

    logger.info("=" * 60)
    logger.info("Starting EnviroTrack pipeline for %s", location)
    logger.info("=" * 60)

    try:
        # Step 1: Ingest fresh weather data
        logger.info("STEP 1/3: Starting weather ingestion")

        raw_file = ingest_weather()

        logger.info(
            "Ingestion completed. Raw file: %s",
            raw_file,
        )

        # Step 2: Process the latest raw weather data
        logger.info("STEP 2/3: Starting hourly processing")

        processing_result = process_latest_weather(
            location=location,
        )

        logger.info(
            "Processing completed: %s",
            processing_result,
        )

        # Step 3: Verify data freshness
        logger.info("STEP 3/3: Checking data freshness")

        freshness_result = monitor_location(location)

        if freshness_result["status"] != "fresh":
            raise RuntimeError(
                "Pipeline completed but freshness check failed: "
                f"{freshness_result['status']}"
            )

        logger.info("=" * 60)
        logger.info("EnviroTrack pipeline completed successfully")
        logger.info("=" * 60)

        return {
            "status": "success",
            "location": location,
            "raw_file": str(raw_file),
            "processing": processing_result,
            "freshness": freshness_result["status"],
        }

    except Exception:
        logger.exception("EnviroTrack pipeline execution failed")
        raise


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
    )

    run_pipeline()
