import os
from datetime import datetime

import psycopg

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://envirotrack:envirotrack_dev@localhost:5433/envirotrack",
)

def insert_raw_weather(
    payload: dict,
    location: str,
    requested_latitude: float,
    requested_longitude: float,
    collected_at,
) -> int:
    with psycopg.connect(DATABASE_URL) as conn, conn.cursor() as cursor:
        cursor.execute(
            """
                INSERT INTO raw_weather_data (
                    source,
                    location_name,
                    requested_latitude,
                    requested_longitude,
                    source_latitude,
                    source_longitude,
                    source_timezone,
                    collected_at,
                    payload
                )
                VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s
                )
                RETURNING id
                """,
            (
                "open-meteo",
                location,
                requested_latitude,
                requested_longitude,
                payload.get("latitude"),
                payload.get("longitude"),
                payload.get("timezone"),
                collected_at,
                psycopg.types.json.Jsonb(payload),
            ),
        )

        raw_id = cursor.fetchone()[0]

        return raw_id


def fetch_latest_raw_weather(location: str) -> dict | None:
    with psycopg.connect(DATABASE_URL) as conn, conn.cursor() as cursor:
        cursor.execute(
            """
                SELECT id, payload
                FROM raw_weather_data
                WHERE location_name = %s
                  AND source = %s
                ORDER BY collected_at DESC, id DESC
                LIMIT 1
                """,
            (location, "open-meteo"),
        )

        row = cursor.fetchone()

        if row is None:
            return None

        return {
            "id": row[0],
            "payload": row[1],
        }


def upsert_hourly_weather(records: list[tuple]) -> dict[str, int]:
    """
    Insert new measurements, update changed measurements,
    and leave unchanged measurements untouched.
    """

    result = {
        "inserted": 0,
        "updated": 0,
        "unchanged": 0,
    }

    if not records:
        return result

    with psycopg.connect(DATABASE_URL) as conn, conn.cursor() as cursor:
        for record in records:
            (
                source,
                location,
                measurement_time,
                temperature,
                humidity,
                precipitation,
                wind_speed,
                raw_data_id,
            ) = record

            cursor.execute(
                """
                INSERT INTO hourly_weather (
                    source,
                    location_name,
                    measurement_time,
                    temperature_celsius,
                    relative_humidity_percent,
                    precipitation_mm,
                    wind_speed_kmh,
                    raw_data_id
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (
                    source,
                    location_name,
                    measurement_time
                )
                DO NOTHING
                RETURNING id
                """,
                record,
            )

            if cursor.fetchone() is not None:
                result["inserted"] += 1
                continue

            cursor.execute(
                """
                UPDATE hourly_weather
                SET
                    temperature_celsius = %s,
                    relative_humidity_percent = %s,
                    precipitation_mm = %s,
                    wind_speed_kmh = %s,
                    raw_data_id = %s,
                    loaded_at = NOW()
                WHERE source = %s
                  AND location_name = %s
                  AND measurement_time = %s
                  AND ROW(
                      temperature_celsius,
                      relative_humidity_percent,
                      precipitation_mm,
                      wind_speed_kmh,
                      raw_data_id
                  ) IS DISTINCT FROM ROW(%s, %s, %s, %s, %s)
                RETURNING id
                """,
                (
                    temperature,
                    humidity,
                    precipitation,
                    wind_speed,
                    raw_data_id,
                    source,
                    location,
                    measurement_time,
                    temperature,
                    humidity,
                    precipitation,
                    wind_speed,
                    raw_data_id,
                ),
            )

            if cursor.fetchone() is not None:
                result["updated"] += 1
            else:
                result["unchanged"] += 1

    return result


def create_pipeline_run(
    pipeline_name: str,
    location: str,
    source: str = "open-meteo",
    source_raw_data_id: int | None = None,
) -> int:
    with psycopg.connect(DATABASE_URL) as conn, conn.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO pipeline_runs (
                pipeline_name,
                source,
                location_name,
                source_raw_data_id,
                status
            )
            VALUES (%s, %s, %s, %s, 'running')
            RETURNING id
            """,
            (pipeline_name, source, location, source_raw_data_id),
        )

        return cursor.fetchone()[0]


def complete_pipeline_run(
    run_id: int,
    records_processed: int,
    records_received: int = 0,
    records_accepted: int = 0,
    records_rejected: int = 0,
    quality_percentage: float | None = None,
    records_inserted: int | None = None,
    records_updated: int | None = None,
    records_unchanged: int | None = None,
) -> None:
    with psycopg.connect(DATABASE_URL) as conn, conn.cursor() as cursor:
        cursor.execute(
            """
            UPDATE pipeline_runs
            SET
                status = 'success',
                records_processed = %s,
                records_received = %s,
                records_accepted = %s,
                records_rejected = %s,
                quality_percentage = %s,
                records_inserted = %s,
                records_updated = %s,
                records_unchanged = %s,
                finished_at = NOW(),
                duration_seconds = EXTRACT(
                    EPOCH FROM (NOW() - started_at)
                )
            WHERE id = %s AND status = 'running'
            """,
            (
                records_processed,
                records_received,
                records_accepted,
                records_rejected,
                quality_percentage,
                records_inserted,
                records_updated,
                records_unchanged,
                run_id,
            ),
        )

        if cursor.rowcount != 1:
            raise RuntimeError(f"Could not complete pipeline run {run_id}")


def set_pipeline_raw_data_id(
    run_id: int,
    raw_data_id: int,
) -> None:
    with psycopg.connect(DATABASE_URL) as conn, conn.cursor() as cursor:
        cursor.execute(
            """
            UPDATE pipeline_runs
            SET source_raw_data_id = %s
            WHERE id = %s
              AND status = 'running'
            """,
            (raw_data_id, run_id),
        )

        if cursor.rowcount != 1:
            raise RuntimeError(
                f"Could not set raw data lineage for pipeline run {run_id}"
            )


def fail_pipeline_run(
    run_id: int,
    error_message: str,
) -> None:
    with psycopg.connect(DATABASE_URL) as conn, conn.cursor() as cursor:
        cursor.execute(
            """
                UPDATE pipeline_runs
                SET
                    status = 'failed',
                    finished_at = NOW(),
                    duration_seconds = EXTRACT(
                        EPOCH FROM (NOW() - started_at)
                    ),
                    error_message = %s
                WHERE id = %s AND status = 'running'
                """,
            (error_message[:5000], run_id),
        )

        if cursor.rowcount != 1:
            raise RuntimeError(f"Could not mark pipeline run {run_id} as failed")


def fetch_latest_collection_time(location: str) -> datetime | None:
    with psycopg.connect(DATABASE_URL) as conn, conn.cursor() as cursor:
        cursor.execute(
            """
            SELECT MAX(collected_at)
            FROM raw_weather_data
            WHERE location_name = %s
              AND source = %s
            """,
            (location, "open-meteo"),
        )

        return cursor.fetchone()[0]
