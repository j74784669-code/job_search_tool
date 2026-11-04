"""Posting-age checks. The other filter lists come from the local filters.yaml."""
from datetime import datetime, timezone

from app import filters

NOW = datetime(2026, 11, 1, 12, 0, tzinfo=timezone.utc)


def test_iso_dates_and_epoch_millis():
    assert filters.posting_too_old("2026-08-02T12:00:00Z", 90, NOW)
    assert not filters.posting_too_old("2026-08-03T12:00:00Z", 90, NOW)
    assert not filters.posting_too_old("2026-09-22T12:38:54-04:00", 90, NOW)
    assert filters.posting_too_old("2026-02-16T07:38:53.841+00:00", 90, NOW)
    assert not filters.posting_too_old("2026-10-08", 90, NOW)
    assert not filters.posting_too_old("2026-09-21T12:55:11", 90, NOW)
    fresh_ms = int(datetime(2026, 8, 3, 12, tzinfo=timezone.utc).timestamp() * 1000)
    assert not filters.posting_too_old(fresh_ms, 90, NOW)
    assert not filters.posting_too_old(str(fresh_ms), 90, NOW)
    old_ms = int(datetime(2026, 1, 1, tzinfo=timezone.utc).timestamp() * 1000)
    assert filters.posting_too_old(old_ms, 90, NOW)


def test_workday_relative_labels():
    assert not filters.posting_too_old("Posted Today", 90, NOW)
    assert not filters.posting_too_old("Posted Yesterday", 90, NOW)
    assert not filters.posting_too_old("Posted 12 Days Ago", 30, NOW)
    assert filters.posting_too_old("Posted 31 Days Ago", 30, NOW)
    # "30+" means older than 30, but not how much. Keep it under a 90-day cap.
    assert not filters.posting_too_old("Posted 30+ Days Ago", 90, NOW)
    assert filters.posting_too_old("Posted 30+ Days Ago", 20, NOW)
    assert filters.posting_age_bounds("Posted 30+ Days Ago", NOW) == (31, None)


def test_missing_and_junk_dates_are_kept():
    for value in (None, "", "Tempe, AZ", "Posted 30+ Days", "not a date"):
        assert not filters.posting_too_old(value, 90, NOW)
    assert not filters.posting_too_old("2020-01-01", None, NOW)


def test_passes_filters_uses_the_age_limit(monkeypatch):
    monkeypatch.setattr(filters, "title_is_relevant", lambda title: True)
    monkeypatch.setattr(filters, "location_is_allowed", lambda location: True)
    monkeypatch.setattr(filters, "jd_stack_mismatch", lambda description: False)
    monkeypatch.setattr(filters, "MAX_POSTING_AGE_DAYS", 90)
    job = {"title": "Engineer", "location": "Remote", "description": "Python"}
    assert filters.passes_filters({**job, "posted_at": "2020-01-01"}) is False
    assert filters.passes_filters({**job, "posted_at": None}) is True
    monkeypatch.setattr(filters, "MAX_POSTING_AGE_DAYS", None)
    assert filters.passes_filters({**job, "posted_at": "2020-01-01"}) is True
