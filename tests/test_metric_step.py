from datetime import UTC, datetime

import pytest

from praxis.metrics.metric_step import MetricStep

_BASE = datetime(2026, 1, 1, tzinfo=UTC)


def test_valid_step_constructs():
    step = MetricStep(_BASE, True, 0.01, 0.009)

    assert step.in_position
    assert step.net_return == 0.009


def test_naive_timestamp_rejected():
    with pytest.raises(ValueError, match='timezone-aware'):
        MetricStep(datetime(2026, 1, 1), True, 0.0, 0.0)


def test_non_finite_gross_return_rejected():
    with pytest.raises(ValueError, match='finite'):
        MetricStep(_BASE, True, float('inf'), 0.0)


def test_non_finite_net_return_rejected():
    with pytest.raises(ValueError, match='finite'):
        MetricStep(_BASE, True, 0.0, float('nan'))
