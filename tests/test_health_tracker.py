'''
Tests for HealthTracker: rolling latency/failure collector.
'''

from __future__ import annotations

import math

import pytest

from praxis.core.health_tracker import HealthTracker


def test_invalid_window_size_rejected() -> None:

    with pytest.raises(ValueError, match='window_size must be a positive int'):
        HealthTracker(window_size=0)


def test_record_request_updates_counters() -> None:

    tracker = HealthTracker()

    tracker.record_request(latency_ms=10.0, succeeded=True)
    tracker.record_request(latency_ms=20.0, succeeded=False)
    tracker.record_request(latency_ms=30.0, succeeded=False)

    snapshot = tracker.snapshot()
    assert snapshot.consecutive_failures == 2
    assert snapshot.failure_rate == pytest.approx(2 / 3)


def test_consecutive_failures_reset_on_success() -> None:

    tracker = HealthTracker()
    for _ in range(3):
        tracker.record_request(latency_ms=5.0, succeeded=False)
    tracker.record_request(latency_ms=5.0, succeeded=True)

    snapshot = tracker.snapshot()
    assert snapshot.consecutive_failures == 0


def test_p99_computed_from_samples() -> None:

    tracker = HealthTracker()
    for value in range(100):
        tracker.record_request(latency_ms=float(value), succeeded=True)

    snapshot = tracker.snapshot()
    assert snapshot.latency_p99_ms == pytest.approx(99.0, abs=1.5)


def test_empty_snapshot_returns_defaults() -> None:

    tracker = HealthTracker()

    snapshot = tracker.snapshot()
    assert snapshot.latency_p99_ms == 0.0
    assert snapshot.consecutive_failures == 0
    assert snapshot.failure_rate == 0.0
    assert snapshot.rate_limit_headroom == 0.0
    assert snapshot.clock_drift_ms == 0.0


def test_snapshot_passes_through_venue_metrics() -> None:

    tracker = HealthTracker()
    tracker.record_request(latency_ms=1.0, succeeded=True)

    snapshot = tracker.snapshot(rate_limit_utilization=0.7, clock_drift_ms=25.0)
    assert snapshot.rate_limit_headroom == 0.7
    assert snapshot.clock_drift_ms == 25.0


def test_window_size_truncates_old_samples() -> None:

    tracker = HealthTracker(window_size=3)
    for value in (100.0, 200.0, 300.0, 400.0):
        tracker.record_request(latency_ms=value, succeeded=True)

    snapshot = tracker.snapshot()
    assert snapshot.latency_p99_ms == pytest.approx(400.0, abs=5.0)
    assert snapshot.latency_p99_ms > 300.0


def test_negative_latency_rejected() -> None:

    tracker = HealthTracker()

    with pytest.raises(ValueError, match='latency_ms must be a finite non-negative number'):
        tracker.record_request(latency_ms=-1.0, succeeded=True)


def test_nan_latency_rejected() -> None:

    tracker = HealthTracker()

    with pytest.raises(ValueError, match='latency_ms must be a finite non-negative number'):
        tracker.record_request(latency_ms=math.nan, succeeded=True)


def test_non_bool_succeeded_rejected() -> None:

    tracker = HealthTracker()

    with pytest.raises(ValueError, match='succeeded must be a bool'):
        tracker.record_request(latency_ms=1.0, succeeded=1)  # type: ignore[arg-type]
