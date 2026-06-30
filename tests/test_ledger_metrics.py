from decimal import Decimal

from praxis.metrics.ledger_metrics import LedgerTrade, ledger_metrics


def _trade(pnl: str, volume: str, is_long: bool = True) -> LedgerTrade:
    return LedgerTrade(is_long=is_long, pnl=Decimal(pnl), volume=Decimal(volume))


def test_empty_trades_all_zero():
    result = ledger_metrics([])

    assert result['expected_value'] == Decimal('0')
    assert result['net_long_volume'] == Decimal('0')
    assert result['net_short_volume'] == Decimal('0')
    assert result['net_trade_volume'] == Decimal('0')


def test_expected_value_is_mean_pnl():
    result = ledger_metrics([_trade('10', '1000'), _trade('-4', '1000'), _trade('6', '1000')])

    assert result['expected_value'] == Decimal('4.00')


def test_volume_split_by_side():
    result = ledger_metrics([
        _trade('5', '1000', is_long=True),
        _trade('3', '500', is_long=True),
        _trade('-2', '700', is_long=False),
    ])

    assert result['net_long_volume'] == Decimal('1500.00')
    assert result['net_short_volume'] == Decimal('700.00')
    assert result['net_trade_volume'] == Decimal('2200.00')


def test_long_only_has_zero_short_volume():
    result = ledger_metrics([_trade('5', '1000'), _trade('5', '2000')])

    assert result['net_short_volume'] == Decimal('0.00')
    assert result['net_trade_volume'] == Decimal('3000.00')


def test_values_rounded_to_two_places():
    result = ledger_metrics([_trade('10', '1000'), _trade('1', '1000'), _trade('1', '1000')])

    assert result['expected_value'] == Decimal('4.00')
