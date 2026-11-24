from datetime import UTC, datetime, timedelta

from envirotrack import freshness


def test_fresh_data_is_classified_correctly(monkeypatch):
    now = datetime(2026, 11, 24, 10, 0, tzinfo=UTC)
    collected_at = now - timedelta(hours=2)

    monkeypatch.setattr(
        freshness,
        "fetch_latest_collection_time",
        lambda location: collected_at,
    )

    result = freshness.check_data_freshness(
        "abbottabad",
        now=now,
    )

    assert result["status"] == "fresh"
    assert result["age_seconds"] == 7200


def test_stale_data_is_classified_correctly(monkeypatch):
    now = datetime(2026, 11, 24, 10, 0, tzinfo=UTC)
    collected_at = now - timedelta(hours=8)

    monkeypatch.setattr(
        freshness,
        "fetch_latest_collection_time",
        lambda location: collected_at,
    )

    result = freshness.check_data_freshness(
        "abbottabad",
        now=now,
    )

    assert result["status"] == "stale"


def test_missing_data_is_classified_correctly(monkeypatch):
    monkeypatch.setattr(
        freshness,
        "fetch_latest_collection_time",
        lambda location: None,
    )

    result = freshness.check_data_freshness("abbottabad")

    assert result["status"] == "missing"
    assert result["collected_at"] is None
