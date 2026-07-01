from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from praxis.core.domain.enums import OrderSide
from praxis.core.domain.events import FillReceived
from praxis.infrastructure.venue_adapter import SymbolFilters
from praxis.replay.build_replay_report import build_replay_report
from praxis.replay.replay_scenario import ReplayBar, ReplayScenario

_BASE = datetime(2022, 1, 1, tzinfo=UTC)
_INTERVAL = 900
_NS = 1_000_000_000


def _filters() -> SymbolFilters:
    return SymbolFilters(
        symbol='BTCUSDT', tick_size=Decimal('0.01'), lot_step=Decimal('0.00001'),
        lot_min=Decimal('0.00001'), lot_max=Decimal('9000'), min_notional=Decimal('10'),
    )


def _bar(index: int, close: str) -> ReplayBar:
    ts_ns = int(_BASE.timestamp()) * _NS + index * _INTERVAL * _NS
    settle = _BASE + timedelta(seconds=(index + 1) * _INTERVAL)
    return ReplayBar(ts_ns=ts_ns, settle=settle, close=float(close), prediction=1, probability=0.6)


def _scenario(bars: list[ReplayBar], capital: str = '20000') -> ReplayScenario:
    return ReplayScenario(
        account_id='t', series='time_15m', interval_seconds=_INTERVAL, symbol='BTCUSDT',
        capital_pool=Decimal(capital), filters=_filters(), strategy_source='x', bars=tuple(bars),
    )


def _fill(index: int, side: OrderSide, qty: str, price: str, fee: str, tid: str = 'a') -> FillReceived:
    settle = _BASE + timedelta(seconds=(index + 1) * _INTERVAL)
    return FillReceived(
        account_id='t', timestamp=settle + timedelta(seconds=1), client_order_id=f'c{index}{side.value}',
        venue_order_id=f'v{index}', venue_trade_id=f'vt{index}', trade_id=tid,
        command_id=f'cmd{index}{side.value}', symbol='BTCUSDT', side=side, qty=Decimal(qty),
        price=Decimal(price), fee=Decimal(fee), fee_asset='USDT', is_maker=False,
    )


def test_pairs_roundtrips_with_pnl_and_fees():
    bars = [_bar(i, '100') for i in range(4)]
    fills = [
        _fill(0, OrderSide.BUY, '1', '100', '0.1'),
        _fill(2, OrderSide.SELL, '1', '110', '0.11'),
    ]
    trades, metrics = build_replay_report(_scenario(bars), fills)

    assert len(trades) == 1
    trade = trades[0]
    assert trade.entry_price == Decimal('100')
    assert trade.exit_price == Decimal('110')
    assert trade.gross_pnl == Decimal('10')
    assert trade.fees == Decimal('0.21')
    assert trade.net_pnl == Decimal('9.79')
    assert trade.bars_held == 2
    assert metrics.trade_count == 1
    assert metrics.win_count == 1
    assert metrics.loss_count == 0
    assert metrics.win_rate == Decimal('100')
    assert metrics.open_position_qty == Decimal('0')


def test_pairs_scaled_entries_fifo_and_reconciles_closed_pnl():
    bars = [_bar(i, '100') for i in range(5)]
    fills = [
        _fill(0, OrderSide.BUY, '1', '100', '0.10'),
        _fill(1, OrderSide.BUY, '1', '110', '0.11'),
        _fill(3, OrderSide.SELL, '2', '120', '0.24'),
    ]
    trades, metrics = build_replay_report(_scenario(bars), fills)

    assert len(trades) == 2
    assert trades[0].qty == Decimal('1')
    assert trades[0].gross_pnl == Decimal('20')
    assert trades[0].fees == Decimal('0.22')
    assert trades[0].net_pnl == Decimal('19.78')
    assert trades[1].qty == Decimal('1')
    assert trades[1].gross_pnl == Decimal('10')
    assert trades[1].fees == Decimal('0.23')
    assert trades[1].net_pnl == Decimal('9.77')
    assert metrics.gross_pnl == Decimal('30')
    assert metrics.net_pnl == Decimal('29.55')
    assert metrics.total_fees == Decimal('0.45')
    assert metrics.open_position_qty == Decimal('0')


def test_partial_exit_keeps_residual_lot_and_allocates_fees_exactly():
    bars = [_bar(i, '100') for i in range(5)]
    fills = [
        _fill(0, OrderSide.BUY, '3', '100', '0.30'),
        _fill(1, OrderSide.SELL, '1', '110', '0.11'),
        _fill(3, OrderSide.SELL, '2', '120', '0.24'),
    ]
    trades, metrics = build_replay_report(_scenario(bars), fills)

    assert len(trades) == 2
    assert trades[0].qty == Decimal('1')
    assert trades[0].gross_pnl == Decimal('10')
    assert trades[0].fees == Decimal('0.21')
    assert trades[0].net_pnl == Decimal('9.79')
    assert trades[1].qty == Decimal('2')
    assert trades[1].gross_pnl == Decimal('40')
    assert trades[1].fees == Decimal('0.44')
    assert trades[1].net_pnl == Decimal('39.56')
    assert metrics.gross_pnl == Decimal('50')
    assert metrics.total_fees == Decimal('0.65')
    assert metrics.net_pnl == Decimal('49.35')
    assert metrics.open_position_qty == Decimal('0')


def test_open_tail_after_closed_trade_reports_closed_only_and_open_qty():
    bars = [_bar(i, '100') for i in range(5)]
    fills = [
        _fill(0, OrderSide.BUY, '1', '100', '0.10'),
        _fill(1, OrderSide.SELL, '1', '110', '0.11'),
        _fill(2, OrderSide.BUY, '2', '120', '0.24'),
    ]
    trades, metrics = build_replay_report(_scenario(bars), fills)

    assert len(trades) == 1
    assert metrics.net_pnl == Decimal('9.79')
    assert metrics.total_fees == Decimal('0.45')
    assert metrics.open_position_qty == Decimal('2')
    assert metrics.final_equity == Decimal('19969.55')


def test_report_sorts_out_of_order_fills_by_timestamp():
    bars = [_bar(i, '100') for i in range(4)]
    buy = _fill(0, OrderSide.BUY, '1', '100', '0.10')
    sell = _fill(2, OrderSide.SELL, '1', '110', '0.11')
    trades, metrics = build_replay_report(_scenario(bars), [sell, buy])

    assert len(trades) == 1
    assert trades[0].gross_pnl == Decimal('10')
    assert trades[0].net_pnl == Decimal('9.79')
    assert metrics.trade_count == 1


def test_same_bar_entry_and_exit_has_zero_bars_held_and_applies_both_fills():
    bars = [_bar(i, '100') for i in range(3)]
    settle = _BASE + timedelta(seconds=_INTERVAL)
    buy = FillReceived(
        account_id='t', timestamp=settle + timedelta(seconds=1), client_order_id='cb',
        venue_order_id='vb', venue_trade_id='vtb', trade_id='a', command_id='cmdb',
        symbol='BTCUSDT', side=OrderSide.BUY, qty=Decimal('1'), price=Decimal('100'),
        fee=Decimal('0.10'), fee_asset='USDT', is_maker=False,
    )
    sell = FillReceived(
        account_id='t', timestamp=settle + timedelta(seconds=1, microseconds=1), client_order_id='cs',
        venue_order_id='vs', venue_trade_id='vts', trade_id='a', command_id='cmds',
        symbol='BTCUSDT', side=OrderSide.SELL, qty=Decimal('1'), price=Decimal('110'),
        fee=Decimal('0.11'), fee_asset='USDT', is_maker=False,
    )
    trades, metrics = build_replay_report(_scenario(bars, capital='10000'), [buy, sell])

    assert len(trades) == 1
    assert trades[0].bars_held == 0
    assert trades[0].gross_pnl == Decimal('10')
    assert trades[0].net_pnl == Decimal('9.79')
    assert metrics.final_equity == Decimal('10009.79')


def test_no_fills_metrics_are_finite_and_empty():
    bars = [_bar(i, '100') for i in range(3)]
    trades, metrics = build_replay_report(_scenario(bars), [])

    assert trades == ()
    assert metrics.trade_count == 0
    assert metrics.win_count == 0
    assert metrics.loss_count == 0
    assert metrics.win_rate is None
    assert metrics.avg_win is None
    assert metrics.avg_loss is None
    assert metrics.profit_factor is None
    assert metrics.sharpe is None
    assert metrics.gross_pnl == Decimal('0')
    assert metrics.net_pnl == Decimal('0')
    assert metrics.total_fees == Decimal('0')
    assert metrics.pnl_pct == Decimal('0')
    assert metrics.max_drawdown_pct == Decimal('0')
    assert metrics.exposure_pct == Decimal('0')
    assert metrics.open_position_qty == Decimal('0')
    assert metrics.final_equity == Decimal('20000')


def test_all_wins_metric_conventions():
    bars = [_bar(i, '100') for i in range(6)]
    fills = [
        _fill(0, OrderSide.BUY, '1', '100', '0'),
        _fill(1, OrderSide.SELL, '1', '110', '0'),
        _fill(2, OrderSide.BUY, '1', '100', '0'),
        _fill(3, OrderSide.SELL, '1', '105', '0'),
    ]
    _, metrics = build_replay_report(_scenario(bars), fills)

    assert metrics.loss_count == 0
    assert metrics.avg_loss is None
    assert metrics.profit_factor is None


def test_all_losses_metric_conventions():
    bars = [_bar(i, '100') for i in range(6)]
    fills = [
        _fill(0, OrderSide.BUY, '1', '100', '0'),
        _fill(1, OrderSide.SELL, '1', '90', '0'),
        _fill(2, OrderSide.BUY, '1', '100', '0'),
        _fill(3, OrderSide.SELL, '1', '95', '0'),
    ]
    _, metrics = build_replay_report(_scenario(bars), fills)

    assert metrics.win_count == 0
    assert metrics.avg_win is None
    assert metrics.profit_factor == Decimal('0')


def test_break_even_trade_is_neither_win_nor_loss():
    bars = [_bar(i, '100') for i in range(4)]
    fills = [
        _fill(0, OrderSide.BUY, '1', '100', '0'),
        _fill(1, OrderSide.SELL, '1', '100', '0'),
    ]
    _, metrics = build_replay_report(_scenario(bars), fills)

    assert metrics.win_count == 0
    assert metrics.loss_count == 0
    assert metrics.win_rate == Decimal('0')
    assert metrics.avg_win is None
    assert metrics.avg_loss is None
    assert metrics.profit_factor is None


def test_single_bar_open_position_has_no_sharpe_and_finite_drawdown():
    bars = [_bar(0, '100')]
    fills = [_fill(0, OrderSide.BUY, '1', '100', '0.10')]
    _, metrics = build_replay_report(_scenario(bars), fills)

    assert metrics.sharpe is None
    assert metrics.exposure_pct == Decimal('100')
    assert metrics.max_drawdown_pct == Decimal('0')
    assert metrics.final_equity == Decimal('19999.90')


def test_equity_touching_zero_does_not_emit_nan_or_inf():
    bars = [_bar(0, '100'), _bar(1, '0.01'), _bar(2, '100')]
    fills = [_fill(0, OrderSide.BUY, '1', '20000', '0')]
    _, metrics = build_replay_report(_scenario(bars, capital='20000'), fills)

    assert metrics.max_drawdown_pct.is_finite()
    assert metrics.max_drawdown_pct >= Decimal('99')
    assert metrics.sharpe is None or metrics.sharpe.is_finite()
    assert metrics.final_equity > Decimal('0')


def test_sharpe_none_for_nonpositive_interval():
    bars = [_bar(0, '100'), _bar(1, '101'), _bar(2, '102')]
    fills = [_fill(0, OrderSide.BUY, '1', '100', '0')]
    scenario = ReplayScenario(
        account_id='t', series='time_15m', interval_seconds=0, symbol='BTCUSDT',
        capital_pool=Decimal('100'), filters=_filters(), strategy_source='x', bars=tuple(bars),
    )
    _, metrics = build_replay_report(scenario, fills)

    assert metrics.sharpe is None


def test_total_fees_includes_open_position_fee():
    bars = [_bar(i, '100') for i in range(3)]
    fills = [
        _fill(0, OrderSide.BUY, '1', '100', '0.10'),
        _fill(1, OrderSide.SELL, '1', '110', '0.11'),
        _fill(2, OrderSide.BUY, '1', '100', '0.20'),
    ]
    _, metrics = build_replay_report(_scenario(bars), fills)

    assert metrics.total_fees == Decimal('0.41')


def test_closed_report_reconciles_to_fill_cashflows():
    bars = [_bar(i, '100') for i in range(5)]
    fills = [
        _fill(0, OrderSide.BUY, '3', '100', '0.30'),
        _fill(1, OrderSide.SELL, '1', '110', '0.11'),
        _fill(3, OrderSide.SELL, '2', '120', '0.24'),
    ]
    scenario = _scenario(bars)
    trades, metrics = build_replay_report(scenario, fills)

    buy_notional = sum(f.qty * f.price for f in fills if f.side is OrderSide.BUY)
    sell_notional = sum(f.qty * f.price for f in fills if f.side is OrderSide.SELL)
    fees = sum(f.fee for f in fills)

    assert metrics.gross_pnl == sell_notional - buy_notional
    assert metrics.total_fees == fees
    assert metrics.net_pnl == sell_notional - buy_notional - fees
    assert metrics.final_equity == scenario.capital_pool + metrics.net_pnl
    assert sum((t.net_pnl for t in trades), Decimal('0')) == metrics.net_pnl


def test_sell_exceeding_open_position_is_rejected():
    bars = [_bar(i, '100') for i in range(3)]
    fills = [
        _fill(0, OrderSide.BUY, '1', '100', '0.10'),
        _fill(1, OrderSide.SELL, '2', '110', '0.22'),
    ]
    with pytest.raises(ValueError, match='sell qty exceeds open position'):
        build_replay_report(_scenario(bars), fills)


def test_sell_without_position_is_rejected():
    bars = [_bar(i, '100') for i in range(2)]
    fills = [_fill(0, OrderSide.SELL, '1', '100', '0.1')]
    with pytest.raises(ValueError, match='sell qty exceeds open position'):
        build_replay_report(_scenario(bars), fills)


def test_concurrent_positions_paired_by_trade_id_not_global_fifo():
    bars = [_bar(i, '150') for i in range(5)]
    fills = [
        _fill(0, OrderSide.BUY, '1', '100', '0', tid='a'),
        _fill(1, OrderSide.BUY, '2', '200', '0', tid='b'),
        _fill(2, OrderSide.SELL, '2', '190', '0', tid='b'),
        _fill(3, OrderSide.SELL, '1', '110', '0', tid='a'),
    ]
    trades, metrics = build_replay_report(_scenario(bars), fills)

    assert len(trades) == 2
    assert trades[0].entry_price == Decimal('100')
    assert trades[0].exit_price == Decimal('110')
    assert trades[0].qty == Decimal('1')
    assert trades[0].gross_pnl == Decimal('10')
    assert trades[1].entry_price == Decimal('200')
    assert trades[1].exit_price == Decimal('190')
    assert trades[1].qty == Decimal('2')
    assert trades[1].gross_pnl == Decimal('-20')
    assert metrics.win_count == 1
    assert metrics.loss_count == 1
    assert metrics.gross_pnl == Decimal('-10')
    assert metrics.open_position_qty == Decimal('0')


def test_open_position_excluded_from_trades():
    bars = [_bar(i, '100') for i in range(3)]
    fills = [_fill(0, OrderSide.BUY, '2', '100', '0.2')]
    trades, metrics = build_replay_report(_scenario(bars), fills)

    assert trades == ()
    assert metrics.trade_count == 0
    assert metrics.win_rate is None
    assert metrics.profit_factor is None
    assert metrics.sharpe is None
    assert metrics.open_position_qty == Decimal('2')


def test_win_rate_and_profit_factor_over_mixed_trades():
    bars = [_bar(i, '100') for i in range(6)]
    fills = [
        _fill(0, OrderSide.BUY, '1', '100', '0'),
        _fill(1, OrderSide.SELL, '1', '120', '0'),
        _fill(2, OrderSide.BUY, '1', '100', '0'),
        _fill(3, OrderSide.SELL, '1', '90', '0'),
    ]
    _trades, metrics = build_replay_report(_scenario(bars), fills)

    assert metrics.trade_count == 2
    assert metrics.win_count == 1
    assert metrics.loss_count == 1
    assert metrics.win_rate == Decimal('50')
    assert metrics.gross_pnl == Decimal('10')
    assert metrics.avg_win == Decimal('20')
    assert metrics.avg_loss == Decimal('-10')
    assert metrics.profit_factor == Decimal('2')


def test_drawdown_and_exposure_from_equity():
    bars = [_bar(0, '100'), _bar(1, '80'), _bar(2, '120')]
    fills = [_fill(0, OrderSide.BUY, '1', '100', '0')]
    _, metrics = build_replay_report(_scenario(bars, capital='100'), fills)

    assert metrics.exposure_pct == Decimal('100')
    assert metrics.max_drawdown_pct == Decimal('20')


def test_drawdown_surfaces_negative_equity_wipeout():
    bars = [_bar(0, '200'), _bar(1, '50')]
    fills = [_fill(0, OrderSide.BUY, '1', '200', '0')]
    _, metrics = build_replay_report(_scenario(bars, capital='100'), fills)

    assert metrics.final_equity < Decimal('0')
    assert metrics.max_drawdown_pct > Decimal('100')


def test_net_pnl_pct_against_capital():
    bars = [_bar(i, '100') for i in range(4)]
    fills = [
        _fill(0, OrderSide.BUY, '1', '100', '0'),
        _fill(2, OrderSide.SELL, '1', '110', '0'),
    ]
    _, metrics = build_replay_report(_scenario(bars, capital='1000'), fills)

    assert metrics.net_pnl == Decimal('10')
    assert metrics.pnl_pct == Decimal('1')


def test_sharpe_positive_for_rising_equity():
    bars = [_bar(0, '100'), _bar(1, '101'), _bar(2, '102'), _bar(3, '103')]
    fills = [_fill(0, OrderSide.BUY, '1', '100', '0')]
    _, metrics = build_replay_report(_scenario(bars, capital='100'), fills)

    assert metrics.sharpe is not None
    assert metrics.sharpe > 0


def test_limen_snapshot_per_trade_on_notional_basis():
    bars = [_bar(i, str(100 + i)) for i in range(5)]
    fills = [_fill(0, OrderSide.BUY, '1', '100', '0.10'), _fill(2, OrderSide.SELL, '1', '110', '0.11')]
    _, metrics = build_replay_report(_scenario(bars, capital='10000'), fills)

    assert metrics.snapshot['trade_pnl_net_bps_p50'] == 979.0
    assert metrics.snapshot['cost_drag_bps_p50'] == 21.0


def test_portfolio_snapshot_diluted_by_idle_capital():
    bars = [_bar(i, str(100 + i)) for i in range(5)]
    fills = [_fill(0, OrderSide.BUY, '1', '100', '0.10'), _fill(2, OrderSide.SELL, '1', '110', '0.11')]
    _, metrics = build_replay_report(_scenario(bars, capital='10000'), fills)

    assert metrics.snapshot_portfolio['trade_pnl_net_bps_p50'] < metrics.snapshot['trade_pnl_net_bps_p50']


def test_scalar_metrics_present_on_report():
    bars = [_bar(i, str(100 + i)) for i in range(5)]
    fills = [_fill(0, OrderSide.BUY, '1', '100', '0'), _fill(2, OrderSide.SELL, '1', '110', '0')]
    _, metrics = build_replay_report(_scenario(bars), fills)

    assert metrics.expected_value == Decimal('10.00')
    assert metrics.net_long_volume == Decimal('100.00')
    assert metrics.net_trade_volume == Decimal('100.00')


def test_snapshots_empty_for_no_fills():
    bars = [_bar(i, str(100 + i)) for i in range(3)]
    _, metrics = build_replay_report(_scenario(bars), [])

    assert metrics.snapshot['trade_pnl_net_bps_p50'] is None
    assert metrics.expected_value == Decimal('0')


def test_entry_fee_reflected_in_position_basis_net():
    bars = [_bar(i, str(100 + i)) for i in range(5)]
    no_fee = [_fill(0, OrderSide.BUY, '1', '100', '0'), _fill(2, OrderSide.SELL, '1', '110', '0')]
    with_fee = [_fill(0, OrderSide.BUY, '1', '100', '0.50'), _fill(2, OrderSide.SELL, '1', '110', '0')]
    _, metrics_no_fee = build_replay_report(_scenario(bars, capital='10000'), no_fee)
    _, metrics_fee = build_replay_report(_scenario(bars, capital='10000'), with_fee)

    assert (
        metrics_fee.snapshot['rolling_return_net_bps_p50']
        < metrics_no_fee.snapshot['rolling_return_net_bps_p50']
    )
