from datetime import UTC, datetime
from uuid import uuid4

import psycopg
import pytest

from envirotrack import db


def test_hourly_upsert_rolls_back_entire_transaction():
    location = f"transaction_test_{uuid4().hex[:12]}"
    measurement_time = datetime(2026, 11, 24, 10, 0, tzinfo=UTC)

    records = [
        (
            "open-meteo",
            location,
            measurement_time,
            22.5,
            65.0,
            0.0,
            12.0,
            None,
        ),
        (
            "open-meteo",
            location,
            datetime(2026, 11, 24, 11, 0, tzinfo=UTC),
            23.0,
            150.0,  # Invalid humidity: database constraint violation
            0.0,
            12.0,
            None,
        ),
    ]

    try:
        with pytest.raises(psycopg.errors.CheckViolation):
            db.upsert_hourly_weather(records)

        with psycopg.connect(db.DATABASE_URL) as conn, conn.cursor() as cursor:
            cursor.execute(
                """
                    SELECT COUNT(*)
                    FROM hourly_weather
                    WHERE location_name = %s
                    """,
                (location,),
            )

            remaining_records = cursor.fetchone()[0]

        assert remaining_records == 0

    finally:
        with psycopg.connect(db.DATABASE_URL) as conn, conn.cursor() as cursor:
            cursor.execute(
                """
                    DELETE FROM hourly_weather
                    WHERE location_name = %s
                    """,
                (location,),
            )


def test_hourly_upsert_tracks_insert_update_and_unchanged():
    location = f"upsert_test_{uuid4().hex[:12]}"
    measurement_time = datetime(2026, 11, 24, 10, 0, tzinfo=UTC)

    original = (
        "open-meteo",
        location,
        measurement_time,
        22.5,
        65.0,
        0.0,
        12.0,
        None,
    )

    changed = (
        "open-meteo",
        location,
        measurement_time,
        25.0,
        70.0,
        0.0,
        14.0,
        None,
    )

    try:
        first = db.upsert_hourly_weather([original])
        second = db.upsert_hourly_weather([original])
        third = db.upsert_hourly_weather([changed])

        assert first == {
            "inserted": 1,
            "updated": 0,
            "unchanged": 0,
        }

        assert second == {
            "inserted": 0,
            "updated": 0,
            "unchanged": 1,
        }

        assert third == {
            "inserted": 0,
            "updated": 1,
            "unchanged": 0,
        }

        with psycopg.connect(db.DATABASE_URL) as conn, conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT COUNT(*), MAX(temperature_celsius)
                FROM hourly_weather
                WHERE location_name = %s
                """,
                (location,),
            )

            count, temperature = cursor.fetchone()

        assert count == 1
        assert temperature == 25.0

    finally:
        with psycopg.connect(db.DATABASE_URL) as conn, conn.cursor() as cursor:
            cursor.execute(
                """
                DELETE FROM hourly_weather
                WHERE location_name = %s
                """,
                (location,),
            )


def test_pipeline_run_records_raw_data_lineage():
    location = f"lineage_test_{uuid4().hex[:12]}"
    collected_at = datetime.now(UTC)

    raw_data_id = None

    try:
        raw_data_id = db.insert_raw_weather(
            payload={
                "timezone": "Asia/Karachi",
                "hourly": {"time": []},
            },
            location=location,
            requested_latitude=34.1688,
            requested_longitude=73.2215,
            collected_at=collected_at,
        )

        run_id = db.create_pipeline_run(
            pipeline_name="hourly_weather_processing",
            location=location,
            source_raw_data_id=raw_data_id,
        )

        with psycopg.connect(db.DATABASE_URL) as conn, conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT source_raw_data_id, status
                FROM pipeline_runs
                WHERE id = %s
                """,
                (run_id,),
            )

            stored_raw_data_id, status = cursor.fetchone()

        assert stored_raw_data_id == raw_data_id
        assert status == "running"

    finally:
        with psycopg.connect(db.DATABASE_URL) as conn, conn.cursor() as cursor:
            cursor.execute(
                "DELETE FROM pipeline_runs WHERE location_name = %s",
                (location,),
            )

            cursor.execute(
                "DELETE FROM raw_weather_data WHERE location_name = %s",
                (location,),
            )


def test_pipeline_run_rejects_nonexistent_raw_data_id():
    location = f"lineage_fk_test_{uuid4().hex[:12]}"

    with pytest.raises(psycopg.errors.ForeignKeyViolation):
        db.create_pipeline_run(
            pipeline_name="hourly_weather_processing",
            location=location,
            source_raw_data_id=-1,
        )
