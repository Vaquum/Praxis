'''
Tests for HealthSnapshot dataclass invariants.
'''

from __future__ import annotations

import math
from dataclasses import FrozenInstanceError

import pytest

from praxis.core.domain.health_snapshot import HealthSnapshot


def test_defaults_represent_healthy_state() -> None:

    snapshot = HealthSnapshot()

    assert snapshot.latency_p99_ms == 0.0
    assert snapshot.consecutive_failures == 0
    assert snapshot.failure_rate == 0.0
    assert snapshot.rate_limit_headroom == 0.0
    assert snapshot.clock_drift_ms == 0.0


def test_custom_values_construct() -> None:

    snapshot = HealthSnapshot(
        latency_p99_ms=120.5,
        consecutive_failures=2,
        failure_rate=0.1,
        rate_limit_headroom=0.75,
        clock_drift_ms=5.0,
    )

    assert snapshot.latency_p99_ms == 120.5
    assert snapshot.consecutive_failures == 2
    assert snapshot.failure_rate == 0.1
    assert snapshot.rate_limit_headroom == 0.75
    assert snapshot.clock_drift_ms == 5.0


@pytest.mark.parametrize(
    'field',
    [
        'latency_p99_ms',
        'failure_rate',
        'rate_limit_headroom',
        'clock_drift_ms',
    ],
)
def test_negative_values_rejected(field: str) -> None:

    kwargs = {field: -0.1}
    with pytest.raises(ValueError, match=f'{field} must be a finite non-negative number'):
        HealthSnapshot(**kwargs)


@pytest.mark.parametrize(
    'field',
    [
        'latency_p99_ms',
        'failure_rate',
        'rate_limit_headroom',
        'clock_drift_ms',
    ],
)
def test_nan_values_rejected(field: str) -> None:

    kwargs = {field: math.nan}
    with pytest.raises(ValueError, match=f'{field} must be a finite non-negative number'):
        HealthSnapshot(**kwargs)


@pytest.mark.parametrize(
    'field',
    [
        'latency_p99_ms',
        'failure_rate',
        'rate_limit_headroom',
        'clock_drift_ms',
    ],
)
def test_bool_values_rejected(field: str) -> None:

    kwargs = {field: True}
    with pytest.raises(ValueError, match=f'{field} must be a finite non-negative number'):
        HealthSnapshot(**kwargs)


@pytest.mark.parametrize(
    'field',
    [
        'failure_rate',
        'rate_limit_headroom',
    ],
)
def test_ratio_above_one_rejected(field: str) -> None:

    kwargs = {field: 1.01}
    with pytest.raises(ValueError, match=f'{field} must be <= 1.0'):
        HealthSnapshot(**kwargs)


def test_consecutive_failures_must_be_int() -> None:

    with pytest.raises(ValueError, match='consecutive_failures must be an int'):
        HealthSnapshot(consecutive_failures=1.5)  # type: ignore[arg-type]


def test_consecutive_failures_bool_rejected() -> None:

    with pytest.raises(ValueError, match='consecutive_failures must be an int'):
        HealthSnapshot(consecutive_failures=True)  # type: ignore[arg-type]


def test_consecutive_failures_negative_rejected() -> None:

    with pytest.raises(ValueError, match='consecutive_failures must be non-negative'):
        HealthSnapshot(consecutive_failures=-1)


def test_ratio_one_accepted() -> None:

    snapshot = HealthSnapshot(failure_rate=1.0, rate_limit_headroom=1.0)

    assert snapshot.failure_rate == 1.0
    assert snapshot.rate_limit_headroom == 1.0


def test_frozen_assignment_rejected() -> None:

    snapshot = HealthSnapshot()

    with pytest.raises(FrozenInstanceError):
        snapshot.latency_p99_ms = 1.0  # type: ignore[misc]
