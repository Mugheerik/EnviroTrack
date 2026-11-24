import logging

from envirotrack.config import PRIMARY_LOCATION
from envirotrack.db import (
    complete_pipeline_run,
    create_pipeline_run,
    fail_pipeline_run,
    fetch_latest_raw_weather,
    set_pipeline_raw_data_id,
    upsert_hourly_weather,
)
from envirotrack.validation import validate_hourly_payload

logger = logging.getLogger(__name__)


def transform_hourly_payload(
    payload: dict,
    raw_data_id: int,
    location: str,
) -> tuple[list[tuple], list[str]]:
    valid_measurements, issues = validate_hourly_payload(payload)

    records = []

    for measurement in valid_measurements:
        records.append(
            (
                "open-meteo",
                location,
                measurement["measurement_time"],
                measurement["temperature_2m"],
                measurement["relative_humidity_2m"],
                measurement["precipitation"],
                measurement["wind_speed_10m"],
                raw_data_id,
            )
        )

    return records, issues


def process_latest_weather(
    location: str = PRIMARY_LOCATION.name,
) -> dict[str, int]:
    logger.info("Starting hourly processing for %s", location)

    run_id = create_pipeline_run(
        pipeline_name="hourly_weather_processing",
        location=location,
    )

    try:
        raw_record = fetch_latest_raw_weather(location)

        if raw_record is None:
            raise RuntimeError(f"No raw weather data found for {location}")

        set_pipeline_raw_data_id(
            run_id=run_id,
            raw_data_id=raw_record["id"],
        )

        payload = raw_record["payload"]

        records, issues = transform_hourly_payload(
            payload=payload,
            raw_data_id=raw_record["id"],
            location=location,
        )

        total_received = len(payload["hourly"]["time"])
        valid_count = len(records)
        rejected_count = total_received - valid_count

        quality_percentage = (
            valid_count / total_received * 100 if total_received else 0.0
        )

        logger.info(
            (
                "Data quality | Location: %s | Received: %s | "
                "Valid: %s | Rejected: %s | Quality: %.2f%%"
            ),
            location,
            total_received,
            valid_count,
            rejected_count,
            quality_percentage,
        )

        if issues:
            logger.warning("Data quality issues found: %s", len(issues))

            for issue in issues[:10]:
                logger.warning("Data quality issue: %s", issue)

            if len(issues) > 10:
                logger.warning(
                    "... and %s additional issues",
                    len(issues) - 10,
                )

        if not records:
            raise ValueError("No valid hourly records available for database loading")

        load_result = upsert_hourly_weather(records)

        processed_count = (
            load_result["inserted"] + load_result["updated"] + load_result["unchanged"]
        )

        complete_pipeline_run(
            run_id=run_id,
            records_processed=processed_count,
            records_received=total_received,
            records_accepted=valid_count,
            records_rejected=rejected_count,
            quality_percentage=quality_percentage,
            records_inserted=load_result["inserted"],
            records_updated=load_result["updated"],
            records_unchanged=load_result["unchanged"],
        )

        logger.info(
            (
                "Processing completed | Run ID: %s | "
                "Inserted: %s | Updated: %s | Unchanged: %s | "
                "Quality: %.2f%%"
            ),
            run_id,
            load_result["inserted"],
            load_result["updated"],
            load_result["unchanged"],
            quality_percentage,
        )

        return load_result

    except Exception as error:
        logger.exception(
            "Processing failed. Run ID: %s",
            run_id,
        )

        try:
            fail_pipeline_run(run_id, str(error))
        except Exception:
            logger.exception(
                "Could not update failed processing run %s",
                run_id,
            )

        raise


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
    )

    process_latest_weather()
