import json
import threading
from datetime import UTC, datetime
from decimal import Decimal

import pytest

from praxis.core.account_ledger import AccountLedger, CostBasisMethod
from praxis.core.domain.chart_of_accounts import Account, is_debit_normal
from praxis.core.domain.enums import FundDirection, OrderSide
from praxis.core.domain.events import FillReceived, FundTransaction, RegisterAccount, TradeClosed

_TS = datetime(2026, 1, 1, tzinfo=UTC)


def _fill(side: OrderSide, qty: str, price: str, fee: str, tid: str = 'a',
          fee_asset: str = 'USDT') -> FillReceived:
    return FillReceived(
        account_id='acc', timestamp=_TS, client_order_id=f'c-{side.value}-{qty}-{price}',
        venue_order_id='v', venue_trade_id='vt', trade_id=tid, command_id='cmd',
        symbol='BTCUSDT', side=side, qty=Decimal(qty), price=Decimal(price),
        fee=Decimal(fee), fee_asset=fee_asset, is_maker=False,
    )


def _register(account_id: str = 'acc', method: CostBasisMethod = CostBasisMethod.FIFO) -> RegisterAccount:
    return RegisterAccount(account_id=account_id, timestamp=_TS, cost_basis_method=method.value)


def _ledger(method: CostBasisMethod = CostBasisMethod.FIFO) -> AccountLedger:
    ledger = AccountLedger('acc')
    ledger.apply(_register(method=method))

    return ledger


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


def test_third_asset_fee_on_buy_raises():
    ledger = _ledger()

    with pytest.raises(NotImplementedError, match='not supported for a buy fill'):
        ledger.apply(_fill(OrderSide.BUY, '1', '100', '0.001', fee_asset='BNB'))


def test_third_asset_fee_on_sell_raises():
    ledger = _ledger()
    ledger.apply(_fill(OrderSide.BUY, '1', '100', '0'))

    with pytest.raises(NotImplementedError, match='not supported for a sell fill'):
        ledger.apply(_fill(OrderSide.SELL, '1', '110', '0.001', fee_asset='BNB'))


def test_base_asset_fee_on_buy_expenses_value_and_reduces_position():
    ledger = _ledger()
    ledger.apply(_fill(OrderSide.BUY, '1', '100', '0.001', fee_asset='BTC'))

    assert ledger.balances[Account.CASH_USDT] == Decimal('-100')
    assert ledger.balances[Account.FEES] == Decimal('0.1')
    assert ledger.balances[Account.CRYPTO_BTC] == Decimal('99.9')
    assert ledger.trades['a'].fees == Decimal('0.1')


def test_base_asset_fee_lot_is_net_received():
    ledger = _ledger()
    ledger.apply(_fill(OrderSide.BUY, '1', '100', '0.001', fee_asset='BTC'))
    ledger.apply(_fill(OrderSide.SELL, '0.999', '110', '0'))

    assert ledger.balances[Account.CRYPTO_BTC] == Decimal('0')
    assert ledger.balances[Account.REALIZED_PNL] == Decimal('9.99')


def test_base_asset_fee_sell_exceeding_net_lot_raises():
    ledger = _ledger()
    ledger.apply(_fill(OrderSide.BUY, '1', '100', '0.001', fee_asset='BTC'))

    with pytest.raises(ValueError, match='sell qty exceeds open lots'):
        ledger.apply(_fill(OrderSide.SELL, '1', '110', '0'))


def test_unsupported_cost_basis_method_rejected():
    with pytest.raises(ValueError, match='cost_basis_method must be one of'):
        RegisterAccount(account_id='acc', timestamp=_TS, cost_basis_method='LIFO')


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


def test_register_account_defaults_to_fifo():
    ledger = AccountLedger('acc')
    ledger.apply(RegisterAccount(account_id='acc', timestamp=_TS))

    assert ledger.cost_basis_method is CostBasisMethod.FIFO


def test_register_account_sets_average_method():
    ledger = _ledger(CostBasisMethod.AVERAGE)

    assert ledger.cost_basis_method is CostBasisMethod.AVERAGE


def test_re_registration_is_rejected_as_immutable():
    ledger = _ledger(CostBasisMethod.FIFO)

    with pytest.raises(ValueError, match='already registered'):
        ledger.apply(_register(method=CostBasisMethod.AVERAGE))


def test_fill_before_registration_raises():
    ledger = AccountLedger('acc')

    with pytest.raises(ValueError, match='not registered'):
        ledger.apply(_fill(OrderSide.BUY, '1', '100', '0'))


def test_trade_closed_before_registration_raises():
    ledger = AccountLedger('acc')

    with pytest.raises(ValueError, match='not registered'):
        ledger.apply(TradeClosed(account_id='acc', timestamp=_TS, trade_id='a', command_id='cmd'))


def test_snapshot_round_trips_registration():
    ledger = _ledger(CostBasisMethod.AVERAGE)
    restored = AccountLedger.from_snapshot(ledger.to_snapshot(1, 1))

    assert restored.cost_basis_method is CostBasisMethod.AVERAGE
    assert restored.state()['registered'] is True


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
    ledger = _ledger(CostBasisMethod.AVERAGE)
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
    fifo = _ledger(CostBasisMethod.FIFO)
    average = _ledger(CostBasisMethod.AVERAGE)

    for side, qty, price in sequence:
        fifo.apply(_fill(side, qty, price, '0'))
        average.apply(_fill(side, qty, price, '0'))

    assert fifo.balances[Account.REALIZED_PNL] == Decimal('20')
    assert average.balances[Account.REALIZED_PNL] == Decimal('15')


def test_snapshot_round_trip_preserves_state():
    ledger = _ledger()
    ledger.apply(_fill(OrderSide.BUY, '2', '100', '0.2'))
    ledger.apply(_fill(OrderSide.SELL, '1', '130', '0.13'))
    snapshot = ledger.to_snapshot(last_applied_event_seq=7, epoch_id=3)
    restored = AccountLedger.from_snapshot(snapshot)

    assert snapshot['last_applied_event_seq'] == 7
    assert snapshot['epoch_id'] == 3
    assert restored.state() == ledger.state()


def test_replay_reproduces_live_state():
    events = [
        _fill(OrderSide.BUY, '2', '100', '0.2'),
        _fill(OrderSide.SELL, '1', '130', '0.13'),
        _fill(OrderSide.BUY, '1', '105', '0', tid='b'),
        TradeClosed(account_id='acc', timestamp=_TS, trade_id='b', command_id='cmd'),
    ]
    live = _ledger()
    replayed = _ledger()

    for event in events:
        live.apply(event)

    for event in events:
        replayed.apply(event)

    assert replayed.state() == live.state()


def test_restored_ledger_realizes_against_restored_lots():
    ledger = _ledger()
    ledger.apply(_fill(OrderSide.BUY, '1', '100', '0'))
    restored = AccountLedger.from_snapshot(ledger.to_snapshot(1, 1))
    restored.apply(_fill(OrderSide.SELL, '1', '110', '0'))

    assert restored.trades['a'].realized_gross == Decimal('10')
    assert restored.balances[Account.REALIZED_PNL] == Decimal('10')


def test_snapshot_does_not_restore_journal():
    ledger = _ledger()
    ledger.apply(_fill(OrderSide.BUY, '1', '100', '0.1'))
    restored = AccountLedger.from_snapshot(ledger.to_snapshot(1, 1))

    assert restored.journal == []
    assert restored.balances[Account.CRYPTO_BTC] == Decimal('100')


def test_snapshot_is_json_serialisable():
    ledger = _ledger()
    ledger.apply(_fill(OrderSide.BUY, '1', '100', '0.1'))
    ledger.apply(_fill(OrderSide.SELL, '1', '110', '0.11'))
    snapshot = ledger.to_snapshot(2, 1)

    assert json.loads(json.dumps(snapshot)) == snapshot


def _fund(direction: FundDirection, amount: str, tx: str = 'f-1') -> FundTransaction:
    return FundTransaction(
        account_id='acc', timestamp=_TS, fund_transaction_id=tx,
        amount=Decimal(amount), direction=direction.value,
    )


def test_deposit_credits_contributions_and_cash():
    ledger = _ledger()
    ledger.apply(_fund(FundDirection.DEPOSIT, '1000'))

    assert ledger.balances[Account.CASH_USDT] == Decimal('1000')
    assert ledger.balances[Account.CONTRIBUTIONS] == Decimal('1000')


def test_withdrawal_debits_contributions_and_cash():
    ledger = _ledger()
    ledger.apply(_fund(FundDirection.DEPOSIT, '1000'))
    ledger.apply(_fund(FundDirection.WITHDRAWAL, '300', tx='f-2'))

    assert ledger.balances[Account.CASH_USDT] == Decimal('700')
    assert ledger.balances[Account.CONTRIBUTIONS] == Decimal('700')


def test_over_withdrawal_is_recorded_not_rejected():
    ledger = _ledger()
    ledger.apply(_fund(FundDirection.WITHDRAWAL, '500'))

    assert ledger.balances[Account.CASH_USDT] == Decimal('-500')
    assert ledger.balances[Account.CONTRIBUTIONS] == Decimal('-500')


def test_fund_transaction_does_not_create_a_trade():
    ledger = _ledger()
    ledger.apply(_fund(FundDirection.DEPOSIT, '1000'))

    assert ledger.trades == {}
    assert len(ledger.journal) == 1
    assert ledger.journal[0].source_event_type == 'FundTransaction'


def test_fund_transaction_before_registration_raises():
    ledger = AccountLedger('acc')

    with pytest.raises(ValueError, match='not registered'):
        ledger.apply(_fund(FundDirection.DEPOSIT, '1000'))


def test_fund_transaction_round_trips_through_snapshot():
    ledger = _ledger()
    ledger.apply(_fund(FundDirection.DEPOSIT, '1000'))
    restored = AccountLedger.from_snapshot(ledger.to_snapshot(1, 1))

    assert restored.balances[Account.CASH_USDT] == Decimal('1000')
    assert restored.balances[Account.CONTRIBUTIONS] == Decimal('1000')


def test_read_balances_returns_a_detached_copy():
    ledger = _ledger()
    ledger.apply(_fund(FundDirection.DEPOSIT, '1000'))
    balances = ledger.read_balances()
    balances[Account.CASH_USDT] = Decimal('0')

    assert ledger.balances[Account.CASH_USDT] == Decimal('1000')
    assert ledger.read_balances()[Account.CASH_USDT] == Decimal('1000')


def test_read_trade_pnls_returns_detached_copies():
    ledger = _ledger()
    ledger.apply(_fill(OrderSide.BUY, '1', '100', '0.1'))
    ledger.apply(_fill(OrderSide.SELL, '1', '110', '0.11'))
    pnls = ledger.read_trade_pnls()
    pnls['a'].realized_gross = Decimal('0')

    assert ledger.trades['a'].realized_gross == Decimal('10')
    assert ledger.read_trade_pnls()['a'].net == Decimal('9.79')


def test_base_asset_fee_not_smaller_than_qty_raises():
    ledger = _ledger()

    with pytest.raises(ValueError, match='must be smaller than the filled qty'):
        ledger.apply(_fill(OrderSide.BUY, '1', '100', '1', fee_asset='BTC'))


def test_concurrent_apply_and_read_never_observe_a_half_applied_event():
    ledger = _ledger()
    inconsistent: list[dict[Account, object]] = []

    def read() -> None:
        for _ in range(500):
            balances = ledger.read_balances()

            if balances[Account.CASH_USDT] != balances[Account.CONTRIBUTIONS]:
                inconsistent.append(balances)

    def write() -> None:
        for index in range(500):
            ledger.apply(_fund(FundDirection.DEPOSIT, '1', tx=f'd{index}'))
            ledger.apply(_fund(FundDirection.WITHDRAWAL, '1', tx=f'w{index}'))

    reader = threading.Thread(target=read)
    writer = threading.Thread(target=write)
    reader.start()
    writer.start()
    reader.join()
    writer.join()

    assert inconsistent == []
    assert ledger.balances[Account.CASH_USDT] == Decimal('0')


def test_event_for_a_different_account_raises():
    ledger = _ledger()

    with pytest.raises(ValueError, match='routed to the ledger'):
        ledger.apply(RegisterAccount(account_id='other-acc', timestamp=_TS))
