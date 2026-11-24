import pytest

from envirotrack.validation import validate_hourly_payload


@pytest.fixture
def valid_payload():
    return {
        "timezone": "Asia/Karachi",
        "hourly": {
            "time": [
                "2026-11-21T10:00",
                "2026-11-21T11:00",
            ],
            "temperature_2m": [22.5, 23.0],
            "relative_humidity_2m": [65, 60],
            "precipitation": [0.0, 0.2],
            "wind_speed_10m": [12.0, 15.0],
        },
    }


def test_valid_payload_is_accepted(valid_payload):
    records, issues = validate_hourly_payload(valid_payload)

    assert len(records) == 2
    assert issues == []
    assert records[0]["temperature_2m"] == 22.5


def test_missing_measurement_is_allowed(valid_payload):
    valid_payload["hourly"]["temperature_2m"][0] = None

    records, issues = validate_hourly_payload(valid_payload)

    assert len(records) == 2
    assert issues == []
    assert records[0]["temperature_2m"] is None


def test_invalid_humidity_rejects_row(valid_payload):
    valid_payload["hourly"]["relative_humidity_2m"][0] = 150

    records, issues = validate_hourly_payload(valid_payload)

    assert len(records) == 1
    assert len(issues) == 1
    assert "above maximum" in issues[0]


def test_negative_precipitation_rejects_row(valid_payload):
    valid_payload["hourly"]["precipitation"][0] = -5

    records, issues = validate_hourly_payload(valid_payload)

    assert len(records) == 1
    assert len(issues) == 1
    assert "below minimum" in issues[0]


def test_mismatched_array_length_raises_error(valid_payload):
    valid_payload["hourly"]["temperature_2m"].pop()

    with pytest.raises(ValueError, match="Array length mismatch"):
        validate_hourly_payload(valid_payload)


def test_missing_hourly_object_raises_error():
    import pytest

    from envirotrack.validation import validate_hourly_payload

    with pytest.raises(TypeError):
        validate_hourly_payload({"hourly": None})
