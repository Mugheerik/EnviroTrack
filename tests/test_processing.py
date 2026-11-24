from datetime import datetime

import pytest

from envirotrack.processing import (
    process_latest_weather,
    transform_hourly_payload,
)


def sample_payload():
    return {
        "timezone": "Asia/Karachi",
        "hourly": {
            "time": ["2026-11-21T10:00"],
            "temperature_2m": [25.0],
            "relative_humidity_2m": [60],
            "precipitation": [0.0],
            "wind_speed_10m": [10.0],
        },
    }


def test_transform_creates_database_record():
    records, issues = transform_hourly_payload(
        payload=sample_payload(),
        raw_data_id=42,
        location="abbottabad",
    )

    assert issues == []
    assert len(records) == 1

    record = records[0]

    assert record[0] == "open-meteo"
    assert record[1] == "abbottabad"
    assert record[3] == 25.0
    assert record[7] == 42
    assert isinstance(record[2], datetime)


def test_processing_loads_latest_raw_record(monkeypatch):
    from envirotrack import processing

    lineage_updates = []

    monkeypatch.setattr(
        processing,
        "fetch_latest_raw_weather",
        lambda location: {
            "id": 42,
            "payload": sample_payload(),
        },
    )

    monkeypatch.setattr(
        processing,
        "set_pipeline_raw_data_id",
        lambda run_id, raw_data_id: lineage_updates.append((run_id, raw_data_id)),
    )

    monkeypatch.setattr(
        processing,
        "upsert_hourly_weather",
        lambda records: {
            "inserted": 1,
            "updated": 0,
            "unchanged": 0,
        },
    )

    result = process_latest_weather("abbottabad")

    assert result == {
        "inserted": 1,
        "updated": 0,
        "unchanged": 0,
    }

    assert len(lineage_updates) == 1
    assert lineage_updates[0][1] == 42


def test_processing_fails_when_no_raw_data(monkeypatch):
    from envirotrack import processing

    monkeypatch.setattr(
        processing,
        "fetch_latest_raw_weather",
        lambda location: None,
    )

    with pytest.raises(RuntimeError, match="No raw weather data"):
        process_latest_weather("abbottabad")


def test_processing_marks_pipeline_failed_when_loading_fails(monkeypatch):
    from envirotrack import processing

    run_id = 202
    failure_message = "Database write failed"
    failed_runs = []
    lineage_updates = []

    raw_record = {
        "id": 55,
        "payload": {
            "hourly": {
                "time": ["2026-11-24T10:00"],
                "temperature_2m": [22.5],
                "relative_humidity_2m": [65],
                "precipitation": [0.0],
                "wind_speed_10m": [12.0],
            }
        },
    }

    monkeypatch.setattr(
        processing,
        "create_pipeline_run",
        lambda **kwargs: run_id,
    )

    monkeypatch.setattr(
        processing,
        "fetch_latest_raw_weather",
        lambda location: raw_record,
    )

    monkeypatch.setattr(
        processing,
        "set_pipeline_raw_data_id",
        lambda run_id, raw_data_id: lineage_updates.append((run_id, raw_data_id)),
    )

    def simulate_database_failure(records):
        raise RuntimeError(failure_message)

    monkeypatch.setattr(
        processing,
        "upsert_hourly_weather",
        simulate_database_failure,
    )

    monkeypatch.setattr(
        processing,
        "fail_pipeline_run",
        lambda run_id, error_message: failed_runs.append((run_id, error_message)),
    )

    with pytest.raises(RuntimeError, match=failure_message):
        processing.process_latest_weather()

    assert lineage_updates == [(run_id, 55)]
    assert failed_runs == [(run_id, failure_message)]
