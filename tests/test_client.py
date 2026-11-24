from envirotrack.client import fetch_weather


class FakeResponse:
    def __init__(self, status_code, payload=None):
        self.status_code = status_code
        self.payload = payload or {}

    def raise_for_status(self):
        if self.status_code >= 400:
            import requests

            raise requests.HTTPError(f"HTTP {self.status_code}")

    def json(self):
        return self.payload


def sample_payload():
    return {
        "current": {
            "temperature_2m": 21.5,
            "relative_humidity_2m": 65,
            "apparent_temperature": 20.8,
            "precipitation": 0.0,
            "rain": 0.0,
            "weather_code": 2,
            "wind_speed_10m": 8.5,
            "time": "2026-11-24T11:00",
        },
        "hourly": {
            "time": ["2026-11-24T11:00"],
        },
        "daily": {
            "time": ["2026-11-24"],
            "temperature_2m_max": [21.6],
            "temperature_2m_min": [13.1],
            "rain_sum": [0.0],
            "precipitation_sum": [0.0],
            "precipitation_probability_max": [0],
            "weather_code": [2],
        },
    }


def test_client_returns_weather_payload(monkeypatch):
    expected = sample_payload()

    monkeypatch.setattr(
        "envirotrack.client.requests.get",
        lambda *args, **kwargs: FakeResponse(200, expected),
    )

    result = fetch_weather(34.1688, 73.2215)

    assert result == expected


def test_client_retries_after_server_error(monkeypatch):
    expected = sample_payload()

    responses = iter(
        [
            FakeResponse(503),
            FakeResponse(200, expected),
        ]
    )

    calls = []

    def fake_get(*args, **kwargs):
        calls.append(1)
        return next(responses)

    monkeypatch.setattr(
        "envirotrack.client.requests.get",
        fake_get,
    )

    monkeypatch.setattr(
        "envirotrack.client.time.sleep",
        lambda seconds: None,
    )

    result = fetch_weather(34.1688, 73.2215)

    assert result == expected
    assert len(calls) == 2


def test_client_does_not_retry_bad_request(monkeypatch):
    calls = []

    def fake_get(*args, **kwargs):
        calls.append(1)
        return FakeResponse(400)

    monkeypatch.setattr(
        "envirotrack.client.requests.get",
        fake_get,
    )

    import requests

    try:
        fetch_weather(34.1688, 73.2215)
    except requests.HTTPError:
        pass
    else:
        raise AssertionError("Expected HTTPError")

    assert len(calls) == 1


def test_client_stops_after_maximum_retries(monkeypatch):
    calls = []

    def fake_get(*args, **kwargs):
        calls.append(1)
        return FakeResponse(503)

    monkeypatch.setattr(
        "envirotrack.client.requests.get",
        fake_get,
    )

    monkeypatch.setattr(
        "envirotrack.client.time.sleep",
        lambda seconds: None,
    )

    import requests

    try:
        fetch_weather(34.1688, 73.2215)
    except requests.HTTPError:
        pass
    else:
        raise AssertionError("Expected HTTPError")

    assert len(calls) == 5
