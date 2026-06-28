from datetime import UTC, datetime
from decimal import Decimal

import pytest

from praxis.core.account_ledger import AccountLedger, CostBasisMethod
from praxis.core.domain.chart_of_accounts import Account, is_debit_normal
from praxis.core.domain.enums import OrderSide
from praxis.core.domain.events import FillReceived, TradeClosed

_TS = datetime(2026, 1, 1, tzinfo=UTC)


def _fill(side: OrderSide, qty: str, price: str, fee: str, tid: str = 'a',
          fee_asset: str = 'USDT') -> FillReceived:
    return FillReceived(
        account_id='acc', timestamp=_TS, client_order_id=f'c-{side.value}-{qty}-{price}',
        venue_order_id='v', venue_trade_id='vt', trade_id=tid, command_id='cmd',
        symbol='BTCUSDT', side=side, qty=Decimal(qty), price=Decimal(price),
        fee=Decimal(fee), fee_asset=fee_asset, is_maker=False,
    )


def _ledger() -> AccountLedger:
    return AccountLedger('acc')


def test_buy_posts_balanced_entry_and_balances():
    ledger = _ledger()
    ledger.apply(_fill(OrderSide.BUY, '1', '100', '0.1'))

    assert len(ledger.journal) == 1
    assert ledger.balances[Account.CRYPTO_BTC] == Decimal('100')
    assert ledger.balances[Account.CASH_USDT] == Decimal('-100.1')
    assert ledger.balances[Account.FEES] == Decimal('0.1')
    assert ledger.balances[Account.REALIZED_PNL] == Decimal('0')


def test_sell_realizes_pnl_against_fifo_cost():
    ledger = _ledger()
    ledger.apply(_fill(OrderSide.BUY, '1', '100', '0.1'))
    ledger.apply(_fill(OrderSide.SELL, '1', '110', '0.11'))

    assert ledger.balances[Account.REALIZED_PNL] == Decimal('10')
    assert ledger.balances[Account.CRYPTO_BTC] == Decimal('0')
    assert ledger.balances[Account.FEES] == Decimal('0.21')
    assert ledger.balances[Account.CASH_USDT] == Decimal('9.79')


def test_fifo_consumes_oldest_lots_first():
    ledger = _ledger()
    ledger.apply(_fill(OrderSide.BUY, '1', '100', '0'))
    ledger.apply(_fill(OrderSide.BUY, '1', '110', '0'))
    ledger.apply(_fill(OrderSide.SELL, '2', '120', '0'))

    assert ledger.balances[Account.REALIZED_PNL] == Decimal('30')
    assert ledger.balances[Account.CRYPTO_BTC] == Decimal('0')
    assert ledger.balances[Account.CASH_USDT] == Decimal('30')


def test_loss_debits_realized_pnl():
    ledger = _ledger()
    ledger.apply(_fill(OrderSide.BUY, '1', '100', '0'))
    ledger.apply(_fill(OrderSide.SELL, '1', '90', '0'))

    assert ledger.balances[Account.REALIZED_PNL] == Decimal('-10')
    assert ledger.balances[Account.CASH_USDT] == Decimal('-10')


def test_partial_sell_leaves_residual_lot():
    ledger = _ledger()
    ledger.apply(_fill(OrderSide.BUY, '3', '100', '0'))
    ledger.apply(_fill(OrderSide.SELL, '1', '120', '0'))

    assert ledger.balances[Account.REALIZED_PNL] == Decimal('20')
    assert ledger.balances[Account.CRYPTO_BTC] == Decimal('200')


def test_sell_exceeding_lots_raises():
    ledger = _ledger()
    ledger.apply(_fill(OrderSide.BUY, '1', '100', '0'))

    with pytest.raises(ValueError, match='sell qty exceeds open lots'):
        ledger.apply(_fill(OrderSide.SELL, '2', '110', '0'))


def test_trade_closed_is_noop():
    ledger = _ledger()
    ledger.apply(_fill(OrderSide.BUY, '1', '100', '0.1'))
    before = dict(ledger.balances)
    journal_len = len(ledger.journal)
    ledger.apply(TradeClosed(account_id='acc', timestamp=_TS, trade_id='a', command_id='cmd'))

    assert ledger.balances == before
    assert len(ledger.journal) == journal_len


def test_non_quote_fee_asset_raises():
    ledger = _ledger()

    with pytest.raises(NotImplementedError, match='not yet supported'):
        ledger.apply(_fill(OrderSide.BUY, '1', '100', '0.001', fee_asset='BNB'))


def test_unsupported_cost_basis_method_rejected():
    with pytest.raises(ValueError, match='unsupported cost_basis_method'):
        AccountLedger('acc', cost_basis_method='LIFO')  # type: ignore[arg-type]


def test_every_entry_is_balanced_and_balances_reconcile():
    ledger = _ledger()
    ledger.apply(_fill(OrderSide.BUY, '2', '100', '0.2'))
    ledger.apply(_fill(OrderSide.SELL, '1', '130', '0.13'))
    ledger.apply(_fill(OrderSide.BUY, '1', '105', '0.105', tid='b'))
    ledger.apply(_fill(OrderSide.SELL, '1', '95', '0.095', tid='b'))

    recomputed = {account: Decimal('0') for account in Account}

    for entry in ledger.journal:
        assert sum(line.debit for line in entry.lines) == sum(line.credit for line in entry.lines)

        for line in entry.lines:
            delta = line.debit - line.credit if is_debit_normal(line.account) else line.credit - line.debit
            recomputed[line.account] += delta

    assert recomputed == ledger.balances


def test_default_cost_basis_is_fifo():
    assert _ledger().cost_basis_method is CostBasisMethod.FIFO


def test_per_trade_pnl_accumulates_gross_and_fees():
    ledger = _ledger()
    ledger.apply(_fill(OrderSide.BUY, '1', '100', '0.1'))
    ledger.apply(_fill(OrderSide.SELL, '1', '110', '0.11'))
    trade = ledger.trades['a']

    assert trade.realized_gross == Decimal('10')
    assert trade.fees == Decimal('0.21')
    assert trade.net == Decimal('9.79')
    assert trade.closed is False


def test_per_trade_pnl_is_isolated_by_trade_id():
    ledger = _ledger()
    ledger.apply(_fill(OrderSide.BUY, '1', '100', '0', tid='a'))
    ledger.apply(_fill(OrderSide.SELL, '1', '110', '0', tid='a'))
    ledger.apply(_fill(OrderSide.BUY, '1', '100', '0', tid='b'))
    ledger.apply(_fill(OrderSide.SELL, '1', '90', '0', tid='b'))

    assert ledger.trades['a'].realized_gross == Decimal('10')
    assert ledger.trades['b'].realized_gross == Decimal('-10')


def test_trade_closed_marks_trade_closed():
    ledger = _ledger()
    ledger.apply(_fill(OrderSide.BUY, '1', '100', '0'))
    ledger.apply(_fill(OrderSide.SELL, '1', '110', '0'))
    ledger.apply(TradeClosed(account_id='acc', timestamp=_TS, trade_id='a', command_id='cmd'))

    assert ledger.trades['a'].closed is True


def test_trade_closed_for_unknown_trade_is_noop():
    ledger = _ledger()
    ledger.apply(TradeClosed(account_id='acc', timestamp=_TS, trade_id='zzz', command_id='cmd'))

    assert ledger.trades == {}


def test_per_trade_realized_matches_realized_pnl_balance_for_single_trade():
    ledger = _ledger()
    ledger.apply(_fill(OrderSide.BUY, '2', '100', '0'))
    ledger.apply(_fill(OrderSide.SELL, '2', '130', '0'))

    assert ledger.trades['a'].realized_gross == ledger.balances[Account.REALIZED_PNL]


def test_average_cost_basis_blends_lot_cost():
    ledger = AccountLedger('acc', CostBasisMethod.AVERAGE)
    ledger.apply(_fill(OrderSide.BUY, '1', '100', '0'))
    ledger.apply(_fill(OrderSide.BUY, '1', '110', '0'))
    ledger.apply(_fill(OrderSide.SELL, '1', '120', '0'))

    assert ledger.balances[Account.REALIZED_PNL] == Decimal('15')
    assert ledger.balances[Account.CRYPTO_BTC] == Decimal('105')


def test_fifo_and_average_differ_on_partial_exit():
    sequence = [
        (OrderSide.BUY, '1', '100'),
        (OrderSide.BUY, '1', '110'),
        (OrderSide.SELL, '1', '120'),
    ]
    fifo = AccountLedger('acc', CostBasisMethod.FIFO)
    average = AccountLedger('acc', CostBasisMethod.AVERAGE)

    for side, qty, price in sequence:
        fifo.apply(_fill(side, qty, price, '0'))
        average.apply(_fill(side, qty, price, '0'))

    assert fifo.balances[Account.REALIZED_PNL] == Decimal('20')
    assert average.balances[Account.REALIZED_PNL] == Decimal('15')
