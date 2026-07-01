from datetime import UTC, datetime, timedelta
from decimal import Decimal

from praxis.core.domain.enums import OrderSide
from praxis.core.domain.events import FillReceived, MarkSampled
from praxis.paper.paper_report import build_paper_report

_BASE = datetime(2026, 1, 1, tzinfo=UTC)
_INTERVAL = 900


def _mark(index: int, price: str) -> MarkSampled:
    return MarkSampled(
        account_id='p', timestamp=_BASE + timedelta(seconds=index * _INTERVAL),
        symbol='BTCUSDT', mark_price=Decimal(price),
    )


def _fill(index: int, side: OrderSide, qty: str, price: str, fee: str) -> FillReceived:
    return FillReceived(
        account_id='p', timestamp=_BASE + timedelta(seconds=index * _INTERVAL + 1),
        client_order_id=f'c{index}{side.value}', venue_order_id='v', venue_trade_id='vt',
        trade_id='a', command_id='cmd', symbol='BTCUSDT', side=side, qty=Decimal(qty),
        price=Decimal(price), fee=Decimal(fee), fee_asset='USDT', is_maker=False,
    )


def test_report_from_events_has_metrics_and_trades():
    events = [
        _mark(0, '100'), _mark(1, '105'), _mark(2, '110'), _mark(3, '108'), _mark(4, '112'),
        _fill(0, OrderSide.BUY, '1', '100', '0.10'),
        _fill(2, OrderSide.SELL, '1', '110', '0.11'),
    ]
    report = build_paper_report(Decimal('10000'), _INTERVAL, events)

    assert report['metrics']['trade_count'] == 1
    assert report['metrics']['snapshot']['trade_pnl_net_bps_p50'] == 979.0
    assert report['metrics']['expected_value'] == '9.79'
    assert len(report['trades']) == 1
    assert isinstance(report['trades'][0]['net_pnl'], str)


def test_report_marks_sorted_regardless_of_event_order():
    events = [
        _mark(4, '112'), _mark(0, '100'), _mark(2, '110'), _mark(1, '105'), _mark(3, '108'),
        _fill(2, OrderSide.SELL, '1', '110', '0'),
        _fill(0, OrderSide.BUY, '1', '100', '0'),
    ]
    report = build_paper_report(Decimal('10000'), _INTERVAL, events)

    assert report['metrics']['trade_count'] == 1


def test_report_no_fills_empty_trades():
    events = [_mark(0, '100'), _mark(1, '101')]
    report = build_paper_report(Decimal('10000'), _INTERVAL, events)

    assert report['trades'] == []
    assert report['metrics']['expected_value'] == '0'


def test_report_decimal_fields_are_strings():
    events = [_mark(0, '100'), _mark(1, '101'), _fill(0, OrderSide.BUY, '1', '100', '0.1')]
    report = build_paper_report(Decimal('10000'), _INTERVAL, events)

    for key in ('gross_pnl', 'net_pnl', 'total_fees', 'final_equity', 'expected_value'):
        assert isinstance(report['metrics'][key], str)


def test_report_drops_duplicate_timestamp_marks():
    dupe = _mark(1, '105')
    events = [_mark(0, '100'), dupe, dupe, _mark(2, '110'), _fill(0, OrderSide.BUY, '1', '100', '0')]
    report = build_paper_report(Decimal('10000'), _INTERVAL, events)

    assert report['metrics']['final_equity'] is not None


def test_report_tolerates_non_increasing_marks_without_raising():
    events = [_mark(2, '110'), _mark(2, '111'), _mark(0, '100'), _mark(1, '105')]
    report = build_paper_report(Decimal('10000'), _INTERVAL, events)

    assert 'metrics' in report
