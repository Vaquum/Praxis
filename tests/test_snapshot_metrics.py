from datetime import UTC, datetime, timedelta

from praxis.metrics.metric_step import MetricStep
from praxis.metrics.snapshot_metrics import snapshot_metrics

_BASE = datetime(2026, 1, 1, tzinfo=UTC)


def _step(day: int, in_pos: bool, gross: float, net: float) -> MetricStep:
    return MetricStep(_BASE + timedelta(days=day), in_pos, gross, net)


def test_empty_steps_all_none():
    result = snapshot_metrics([])

    assert result['cvar_95_return_bps'] is None
    assert result['trade_pnl_net_bps_p50'] is None
    assert result['drawdown_depth_bps_p50'] is None


def test_single_trade_net_and_cost_drag_bps():
    steps = [
        _step(0, False, 0.0, 0.0),
        _step(1, True, 0.010, 0.008),
        _step(2, True, 0.005, 0.004),
        _step(3, False, 0.0, 0.0),
    ]
    result = snapshot_metrics(steps)

    gross_run = (1.010 * 1.005) - 1.0
    net_run = (1.008 * 1.004) - 1.0
    assert result['trade_pnl_net_bps_p50'] == round(net_run * 10_000.0, 1)
    assert result['cost_drag_bps_p50'] == round((gross_run - net_run) * 10_000.0, 1)


def test_edge_per_signal_is_per_held_bar():
    steps = [
        _step(0, True, 0.01, 0.01),
        _step(1, True, 0.03, 0.03),
    ]
    result = snapshot_metrics(steps)

    assert result['edge_per_signal_bps_p5'] is not None
    assert result['edge_per_signal_bps_p50'] == 200.0


def test_two_separate_trades_counted_independently():
    steps = [
        _step(0, True, 0.02, 0.02),
        _step(1, False, 0.0, 0.0),
        _step(2, True, -0.01, -0.01),
        _step(3, False, 0.0, 0.0),
    ]
    result = snapshot_metrics(steps)

    assert result['trade_pnl_net_bps_p50'] == 50.0
    assert result['trade_pnl_net_bps_p5'] < result['trade_pnl_net_bps_p95']


def test_open_trade_at_end_is_closed_for_metrics():
    steps = [_step(0, True, 0.05, 0.05)]
    result = snapshot_metrics(steps)

    assert result['trade_pnl_net_bps_p50'] == 500.0


def test_drawdown_depth_and_duration():
    steps = [
        _step(0, True, 0.10, 0.10),
        _step(1, True, -0.20, -0.20),
        _step(2, True, 0.30, 0.30),
    ]
    result = snapshot_metrics(steps)

    assert result['drawdown_depth_bps_p50'] == -2000.0
    assert result['drawdown_duration_days_p50'] == 1.0


def test_rolling_window_and_cvar_present():
    steps = [_step(d, True, 0.01 * (1 if d % 2 else -1), 0.01 * (1 if d % 2 else -1)) for d in range(10)]
    result = snapshot_metrics(steps, clock_window='1d')

    assert result['rolling_return_net_bps_p50'] is not None
    assert result['return_on_exposure_p50'] is not None
    assert result['cvar_95_return_bps'] is not None


def test_no_positions_no_trades_no_drawdown():
    steps = [_step(d, False, 0.0, 0.0) for d in range(5)]
    result = snapshot_metrics(steps)

    assert result['trade_pnl_net_bps_p50'] is None
    assert result['edge_per_signal_bps_p50'] is None
    assert result['drawdown_depth_bps_p50'] is None


def test_return_on_exposure_limen_excludes_first_step_full_keeps_all():
    nets = [0.0, 0.01, 0.01, 0.01, 0.0]
    steps = [
        MetricStep(_BASE + timedelta(hours=i), i in (1, 2, 3), nets[i], nets[i])
        for i in range(5)
    ]
    result = snapshot_metrics(steps, clock_window='1d')

    window_return = 1.01 ** 3 - 1.0
    roe_full = window_return / (3 / 5) * 10_000.0     # exposure over all 5 steps
    roe_limen = window_return / (3 / 4) * 10_000.0     # first step excluded -> 4 eligible

    assert result['return_on_exposure_p50'] == round(roe_limen, 1)
    assert result['return_on_exposure_full_p50'] == round(roe_full, 1)
    assert result['return_on_exposure_p50'] < result['return_on_exposure_full_p50']


def test_return_on_exposure_full_present_and_none_when_flat():
    flat = [_step(d, False, 0.0, 0.0) for d in range(3)]
    result = snapshot_metrics(flat)

    assert result['return_on_exposure_full_p50'] is None
    assert result['return_on_exposure_p50'] is None
