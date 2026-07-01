from datetime import UTC, datetime, timedelta, tzinfo
from decimal import Decimal

import pytest

from praxis.core.domain.enums import OrderSide
from praxis.core.domain.events import FillReceived
from praxis.paper.paper_metrics import _effective_interval_seconds, build_paper_metrics

_BASE = datetime(2026, 1, 1, tzinfo=UTC)
_INTERVAL = 900


def _mark(index: int, price: str) -> tuple[datetime, Decimal]:
    return (_BASE + timedelta(seconds=index * _INTERVAL), Decimal(price))


def _fill(index: int, side: OrderSide, qty: str, price: str, fee: str, tid: str = 'a') -> FillReceived:
    return FillReceived(
        account_id='p', timestamp=_BASE + timedelta(seconds=index * _INTERVAL + 1),
        client_order_id=f'c{index}{side.value}', venue_order_id='v', venue_trade_id='vt',
        trade_id=tid, command_id='cmd', symbol='BTCUSDT', side=side, qty=Decimal(qty),
        price=Decimal(price), fee=Decimal(fee), fee_asset='USDT', is_maker=False,
    )


def test_paper_metrics_match_shared_core_on_marks():
    marks = [_mark(i, str(100 + i)) for i in range(5)]
    fills = [_fill(0, OrderSide.BUY, '1', '100', '0.10'), _fill(2, OrderSide.SELL, '1', '110', '0.11')]
    trades, metrics = build_paper_metrics(Decimal('10000'), _INTERVAL, fills, marks)

    assert len(trades) == 1
    assert metrics.snapshot['trade_pnl_net_bps_p50'] == 979.0
    assert metrics.snapshot_portfolio['trade_pnl_net_bps_p50'] < metrics.snapshot['trade_pnl_net_bps_p50']
    assert metrics.expected_value == Decimal('9.79')


def test_naive_mark_timestamp_rejected():
    marks = [(datetime(2026, 1, 1), Decimal('100'))]

    with pytest.raises(ValueError, match='timezone-aware'):
        build_paper_metrics(Decimal('10000'), _INTERVAL, [], marks)


def test_non_increasing_marks_rejected():
    marks = [_mark(2, '100'), _mark(1, '101')]

    with pytest.raises(ValueError, match='strictly increase'):
        build_paper_metrics(Decimal('10000'), _INTERVAL, [], marks)


def test_non_positive_mark_price_rejected():
    marks = [(_BASE, Decimal('0'))]

    with pytest.raises(ValueError, match='positive and finite'):
        build_paper_metrics(Decimal('10000'), _INTERVAL, [], marks)


def test_non_positive_interval_rejected():
    with pytest.raises(ValueError, match='interval_seconds must be positive'):
        build_paper_metrics(Decimal('10000'), 0, [], [])


def test_no_fills_empty_metrics():
    marks = [_mark(i, '100') for i in range(3)]
    trades, metrics = build_paper_metrics(Decimal('10000'), _INTERVAL, [], marks)

    assert trades == ()
    assert metrics.expected_value == Decimal('0')
    assert metrics.snapshot['trade_pnl_net_bps_p50'] is None


class _NoOffsetTz(tzinfo):
    def utcoffset(self, _dt: datetime | None) -> None:
        return None

    def tzname(self, _dt: datetime | None) -> None:
        return None

    def dst(self, _dt: datetime | None) -> None:
        return None


def test_tz_aware_but_no_offset_mark_rejected():
    marks = [(datetime(2026, 1, 1, tzinfo=_NoOffsetTz()), Decimal('100'))]

    with pytest.raises(ValueError, match='timezone-aware'):
        build_paper_metrics(Decimal('10000'), _INTERVAL, [], marks)


def test_effective_interval_is_mean_delta_with_gaps():
    marks = [(_BASE, Decimal('100')), (_BASE + timedelta(seconds=60), Decimal('101')),
             (_BASE + timedelta(seconds=300), Decimal('102'))]

    assert _effective_interval_seconds(marks, 60) == 150


def test_effective_interval_regular_marks():
    marks = [(_BASE + timedelta(seconds=60 * i), Decimal('100')) for i in range(5)]

    assert _effective_interval_seconds(marks, 999) == 60


def test_effective_interval_falls_back_below_two_marks():
    assert _effective_interval_seconds([], 60) == 60
    assert _effective_interval_seconds([(_BASE, Decimal('100'))], 60) == 60
