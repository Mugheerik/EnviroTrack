import pytest

from envirotrack import ingestion


def test_ingestion_marks_pipeline_failed_when_database_insert_fails(
    monkeypatch,
    tmp_path,
):
    run_id = 101
    failure_message = "Database connection unavailable"

    payload = {
        "hourly": {
            "time": ["2026-11-24T10:00"],
            "temperature_2m": [22.5],
            "relative_humidity_2m": [65],
            "precipitation": [0.0],
            "wind_speed_10m": [12.0],
        }
    }

    failed_runs = []

    monkeypatch.setattr(
        ingestion,
        "RAW_DATA_DIR",
        tmp_path,
    )

    monkeypatch.setattr(
        ingestion,
        "create_pipeline_run",
        lambda **kwargs: run_id,
    )

    monkeypatch.setattr(
        ingestion,
        "fetch_weather",
        lambda latitude, longitude: payload,
    )

    def simulate_database_failure(**kwargs):
        raise RuntimeError(failure_message)

    monkeypatch.setattr(
        ingestion,
        "insert_raw_weather",
        simulate_database_failure,
    )

    monkeypatch.setattr(
        ingestion,
        "fail_pipeline_run",
        lambda run_id, error_message: failed_runs.append((run_id, error_message)),
    )

    with pytest.raises(RuntimeError, match=failure_message):
        ingestion.ingest_weather()

    assert failed_runs == [(run_id, failure_message)]

    raw_files = list(tmp_path.glob("*.json"))
    assert len(raw_files) == 1
