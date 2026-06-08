'''Tests for praxis.binsim.ledger.Ledger.'''

from __future__ import annotations

import asyncio
import json
import threading
import time
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

import pytest

from praxis.binsim.ledger import (
    DuplicateClientOrderIdError,
    InsufficientBalanceError,
    Ledger,
)
from praxis.core.domain.enums import OrderSide


_ACCT = 'acc-1'
_TS = datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)
_BOUNDED_GROWTH_MARGIN_BYTES = 256
_APPLY_ORDER_GROWTH_FLOOR_BYTES = 1000
_INSTRUMENTED_WRITE_DELAY_SECONDS = 0.05
_WRITE_START_TIMEOUT_SECONDS = 2.0


def _new_ledger(tmp_path: Path) -> Ledger:

    return Ledger(tmp_path)


def test_constructor_rejects_non_path() -> None:

    with pytest.raises(TypeError, match='state_dir must be a Path'):
        Ledger('not-a-path')  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_register_account_seeds_balances(tmp_path: Path) -> None:

    ledger = _new_ledger(tmp_path)
    await ledger.register_account(_ACCT, Decimal('10000'), Decimal('0.5'))

    usdt, btc = await ledger.balance(_ACCT)
    assert usdt == Decimal('10000')
    assert btc == Decimal('0.5')


@pytest.mark.asyncio
async def test_register_account_defaults_btc_to_zero(tmp_path: Path) -> None:

    ledger = _new_ledger(tmp_path)
    await ledger.register_account(_ACCT, Decimal('10000'))

    usdt, btc = await ledger.balance(_ACCT)
    assert usdt == Decimal('10000')
    assert btc == Decimal('0')


@pytest.mark.asyncio
async def test_register_account_rejects_empty_id(tmp_path: Path) -> None:

    ledger = _new_ledger(tmp_path)

    with pytest.raises(ValueError, match='account_id cannot be empty'):
        await ledger.register_account('', Decimal('1'))


@pytest.mark.asyncio
async def test_register_account_rejects_duplicate(tmp_path: Path) -> None:

    ledger = _new_ledger(tmp_path)
    await ledger.register_account(_ACCT, Decimal('1'))

    with pytest.raises(ValueError, match='already registered'):
        await ledger.register_account(_ACCT, Decimal('1'))


@pytest.mark.asyncio
async def test_register_account_rejects_negative_initial_usdt(tmp_path: Path) -> None:

    ledger = _new_ledger(tmp_path)

    with pytest.raises(ValueError, match='initial_usdt must be non-negative'):
        await ledger.register_account(_ACCT, Decimal('-1'))


@pytest.mark.asyncio
async def test_register_account_rejects_negative_initial_btc(tmp_path: Path) -> None:

    ledger = _new_ledger(tmp_path)

    with pytest.raises(ValueError, match='initial_btc must be non-negative'):
        await ledger.register_account(_ACCT, Decimal('1'), Decimal('-1'))


@pytest.mark.asyncio
async def test_balance_raises_for_unregistered_account(tmp_path: Path) -> None:

    ledger = _new_ledger(tmp_path)

    with pytest.raises(KeyError, match='not registered'):
        await ledger.balance(_ACCT)


@pytest.mark.asyncio
async def test_apply_fill_buy_debits_usdt_credits_btc(tmp_path: Path) -> None:

    ledger = _new_ledger(tmp_path)
    await ledger.register_account(_ACCT, Decimal('10000'))

    fill = await ledger.apply_fill(
        _ACCT, OrderSide.BUY, Decimal('0.1'), Decimal('100'),
        Decimal('0.01'), timestamp=_TS,
    )

    usdt, btc = await ledger.balance(_ACCT)
    assert usdt == Decimal('10000') - Decimal('10') - Decimal('0.01')
    assert btc == Decimal('0.1')
    assert fill.trade_id == '1'


@pytest.mark.asyncio
async def test_apply_fill_sell_credits_usdt_debits_btc(tmp_path: Path) -> None:

    ledger = _new_ledger(tmp_path)
    await ledger.register_account(_ACCT, Decimal('0'), Decimal('1'))

    fill = await ledger.apply_fill(
        _ACCT, OrderSide.SELL, Decimal('0.5'), Decimal('100'),
        Decimal('0.05'), timestamp=_TS,
    )

    usdt, btc = await ledger.balance(_ACCT)
    assert usdt == Decimal('50') - Decimal('0.05')
    assert btc == Decimal('0.5')
    assert fill.side is OrderSide.SELL


@pytest.mark.asyncio
async def test_apply_fill_assigns_monotonic_trade_ids(tmp_path: Path) -> None:

    ledger = _new_ledger(tmp_path)
    await ledger.register_account(_ACCT, Decimal('10000'), Decimal('1'))

    f1 = await ledger.apply_fill(_ACCT, OrderSide.BUY, Decimal('0.01'), Decimal('100'), Decimal('0'))
    f2 = await ledger.apply_fill(_ACCT, OrderSide.BUY, Decimal('0.01'), Decimal('100'), Decimal('0'))
    f3 = await ledger.apply_fill(_ACCT, OrderSide.SELL, Decimal('0.01'), Decimal('100'), Decimal('0'))

    assert (f1.trade_id, f2.trade_id, f3.trade_id) == ('1', '2', '3')


@pytest.mark.asyncio
async def test_apply_fill_appends_to_fills_history(tmp_path: Path) -> None:

    ledger = _new_ledger(tmp_path)
    await ledger.register_account(_ACCT, Decimal('10000'))
    await ledger.apply_fill(_ACCT, OrderSide.BUY, Decimal('0.1'), Decimal('100'), Decimal('0'))
    await ledger.apply_fill(_ACCT, OrderSide.BUY, Decimal('0.2'), Decimal('110'), Decimal('0'))

    fills = await ledger.fills(_ACCT)
    assert len(fills) == 2
    assert fills[0].qty == Decimal('0.1')
    assert fills[1].qty == Decimal('0.2')


@pytest.mark.asyncio
async def test_apply_fill_records_fee_and_fee_asset(tmp_path: Path) -> None:

    ledger = _new_ledger(tmp_path)
    await ledger.register_account(_ACCT, Decimal('10000'))

    fill = await ledger.apply_fill(
        _ACCT, OrderSide.BUY, Decimal('0.1'), Decimal('100'),
        Decimal('0.123'), timestamp=_TS,
    )

    assert fill.fee == Decimal('0.123')
    assert fill.fee_asset == 'USDT'


@pytest.mark.asyncio
async def test_apply_fill_rejects_non_usdt_fee_asset(tmp_path: Path) -> None:

    ledger = _new_ledger(tmp_path)
    await ledger.register_account(_ACCT, Decimal('10000'))

    with pytest.raises(ValueError, match='fee_asset must be USDT'):
        await ledger.apply_fill(
            _ACCT, OrderSide.BUY, Decimal('0.1'), Decimal('100'),
            Decimal('0'), fee_asset='BTC',
        )


@pytest.mark.asyncio
async def test_apply_fill_rejects_naive_timestamp(tmp_path: Path) -> None:

    ledger = _new_ledger(tmp_path)
    await ledger.register_account(_ACCT, Decimal('10000'))

    with pytest.raises(ValueError, match='timestamp must be timezone-aware'):
        await ledger.apply_fill(
            _ACCT, OrderSide.BUY, Decimal('0.1'), Decimal('100'),
            Decimal('0'), timestamp=datetime(2026, 1, 1, 12, 0, 0),
        )


@pytest.mark.asyncio
async def test_apply_fill_default_timestamp_is_now(tmp_path: Path) -> None:

    ledger = _new_ledger(tmp_path)
    await ledger.register_account(_ACCT, Decimal('10000'))

    before = datetime.now(UTC)
    fill = await ledger.apply_fill(_ACCT, OrderSide.BUY, Decimal('0.1'), Decimal('100'), Decimal('0'))
    after = datetime.now(UTC)

    assert before <= fill.timestamp <= after


@pytest.mark.asyncio
@pytest.mark.parametrize('bad_qty', [Decimal('0'), Decimal('-0.1')])
async def test_apply_fill_rejects_non_positive_qty(tmp_path: Path, bad_qty: Decimal) -> None:

    ledger = _new_ledger(tmp_path)
    await ledger.register_account(_ACCT, Decimal('10000'))

    with pytest.raises(ValueError, match='qty must be positive'):
        await ledger.apply_fill(_ACCT, OrderSide.BUY, bad_qty, Decimal('100'), Decimal('0'))


@pytest.mark.asyncio
@pytest.mark.parametrize('bad_price', [Decimal('0'), Decimal('-1')])
async def test_apply_fill_rejects_non_positive_price(tmp_path: Path, bad_price: Decimal) -> None:

    ledger = _new_ledger(tmp_path)
    await ledger.register_account(_ACCT, Decimal('10000'))

    with pytest.raises(ValueError, match='price must be positive'):
        await ledger.apply_fill(_ACCT, OrderSide.BUY, Decimal('0.1'), bad_price, Decimal('0'))


@pytest.mark.asyncio
async def test_apply_fill_rejects_negative_fee(tmp_path: Path) -> None:

    ledger = _new_ledger(tmp_path)
    await ledger.register_account(_ACCT, Decimal('10000'))

    with pytest.raises(ValueError, match='fee must be non-negative'):
        await ledger.apply_fill(_ACCT, OrderSide.BUY, Decimal('0.1'), Decimal('100'), Decimal('-0.01'))


@pytest.mark.asyncio
async def test_apply_fill_allows_zero_fee(tmp_path: Path) -> None:

    ledger = _new_ledger(tmp_path)
    await ledger.register_account(_ACCT, Decimal('10000'))

    await ledger.apply_fill(_ACCT, OrderSide.BUY, Decimal('0.1'), Decimal('100'), Decimal('0'))

    usdt, _ = await ledger.balance(_ACCT)
    assert usdt == Decimal('10000') - Decimal('10')


@pytest.mark.asyncio
async def test_apply_fill_raises_when_unknown_account(tmp_path: Path) -> None:

    ledger = _new_ledger(tmp_path)

    with pytest.raises(KeyError, match='not registered'):
        await ledger.apply_fill(_ACCT, OrderSide.BUY, Decimal('0.1'), Decimal('100'), Decimal('0'))


@pytest.mark.asyncio
async def test_apply_fill_buy_raises_when_usdt_insufficient(tmp_path: Path) -> None:

    ledger = _new_ledger(tmp_path)
    await ledger.register_account(_ACCT, Decimal('5'))

    with pytest.raises(InsufficientBalanceError, match='USDT would be'):
        await ledger.apply_fill(_ACCT, OrderSide.BUY, Decimal('0.1'), Decimal('100'), Decimal('0'))


@pytest.mark.asyncio
async def test_apply_fill_buy_includes_fee_in_balance_check(tmp_path: Path) -> None:

    ledger = _new_ledger(tmp_path)
    await ledger.register_account(_ACCT, Decimal('10'))

    with pytest.raises(InsufficientBalanceError, match='USDT would be'):
        await ledger.apply_fill(_ACCT, OrderSide.BUY, Decimal('0.1'), Decimal('100'), Decimal('0.01'))


@pytest.mark.asyncio
async def test_apply_fill_sell_raises_when_btc_insufficient(tmp_path: Path) -> None:

    ledger = _new_ledger(tmp_path)
    await ledger.register_account(_ACCT, Decimal('0'), Decimal('0.05'))

    with pytest.raises(InsufficientBalanceError, match='BTC would be'):
        await ledger.apply_fill(_ACCT, OrderSide.SELL, Decimal('0.1'), Decimal('100'), Decimal('0'))


@pytest.mark.asyncio
async def test_insufficient_balance_does_not_mutate_state(tmp_path: Path) -> None:

    ledger = _new_ledger(tmp_path)
    await ledger.register_account(_ACCT, Decimal('5'))

    with pytest.raises(InsufficientBalanceError):
        await ledger.apply_fill(_ACCT, OrderSide.BUY, Decimal('0.1'), Decimal('100'), Decimal('0'))

    usdt, btc = await ledger.balance(_ACCT)
    assert usdt == Decimal('5')
    assert btc == Decimal('0')

    fills = await ledger.fills(_ACCT)
    assert fills == []


@pytest.mark.asyncio
async def test_snapshot_written_after_register_and_fill(tmp_path: Path) -> None:

    ledger = _new_ledger(tmp_path)
    snapshot = tmp_path / 'binsim_ledger.json'

    await ledger.register_account(_ACCT, Decimal('10000'))
    assert snapshot.exists()

    await ledger.apply_fill(_ACCT, OrderSide.BUY, Decimal('0.1'), Decimal('100'), Decimal('0'))

    payload = json.loads(snapshot.read_text())
    assert payload['next_trade_id'] == 2
    assert _ACCT in payload['accounts']
    assert Decimal(payload['accounts'][_ACCT]['usdt']) == Decimal('9990')
    assert Decimal(payload['accounts'][_ACCT]['btc']) == Decimal('0.1')
    assert 'fills' not in payload['accounts'][_ACCT]


@pytest.mark.asyncio
async def test_snapshot_atomic_temp_file_cleaned_on_success(tmp_path: Path) -> None:

    ledger = _new_ledger(tmp_path)
    await ledger.register_account(_ACCT, Decimal('1'))

    leftover = [p for p in tmp_path.iterdir() if '.tmp' in p.name]
    assert leftover == []


@pytest.mark.asyncio
async def test_load_restores_balances_and_counters(tmp_path: Path) -> None:

    ledger1 = _new_ledger(tmp_path)
    await ledger1.register_account(_ACCT, Decimal('10000'))
    await ledger1.apply_fill(_ACCT, OrderSide.BUY, Decimal('0.1'), Decimal('100'), Decimal('0.01'), timestamp=_TS)
    await ledger1.apply_fill(_ACCT, OrderSide.SELL, Decimal('0.05'), Decimal('110'), Decimal('0.005'), timestamp=_TS)

    ledger2 = _new_ledger(tmp_path)
    await ledger2.load()

    usdt, btc = await ledger2.balance(_ACCT)
    assert usdt == Decimal('10000') - Decimal('10') - Decimal('0.01') + Decimal('5.5') - Decimal('0.005')
    assert btc == Decimal('0.05')

    fills = await ledger2.fills(_ACCT)
    assert fills == []

    next_fill = await ledger2.apply_fill(_ACCT, OrderSide.BUY, Decimal('0.01'), Decimal('100'), Decimal('0'))
    assert next_fill.trade_id == '3'


@pytest.mark.asyncio
async def test_load_is_noop_when_snapshot_missing(tmp_path: Path) -> None:

    ledger = _new_ledger(tmp_path)
    await ledger.load()

    accounts = await ledger.accounts()
    assert accounts == []


@pytest.mark.asyncio
async def test_load_raises_on_corrupt_snapshot(tmp_path: Path) -> None:

    snapshot = tmp_path / 'binsim_ledger.json'
    snapshot.write_text('{not valid json')

    ledger = _new_ledger(tmp_path)

    with pytest.raises(json.JSONDecodeError):
        await ledger.load()


@pytest.mark.asyncio
async def test_fills_returns_copy_not_internal_list(tmp_path: Path) -> None:

    ledger = _new_ledger(tmp_path)
    await ledger.register_account(_ACCT, Decimal('10000'))
    await ledger.apply_fill(_ACCT, OrderSide.BUY, Decimal('0.1'), Decimal('100'), Decimal('0'))

    fills = await ledger.fills(_ACCT)
    fills.clear()

    again = await ledger.fills(_ACCT)
    assert len(again) == 1


@pytest.mark.asyncio
async def test_accounts_lists_all_registered(tmp_path: Path) -> None:

    ledger = _new_ledger(tmp_path)
    await ledger.register_account('a', Decimal('1'))
    await ledger.register_account('b', Decimal('1'))
    await ledger.register_account('c', Decimal('1'))

    accounts = await ledger.accounts()
    assert sorted(accounts) == ['a', 'b', 'c']


@pytest.mark.asyncio
async def test_concurrent_fills_serialised_no_lost_updates(tmp_path: Path) -> None:

    ledger = _new_ledger(tmp_path)
    await ledger.register_account(_ACCT, Decimal('100000'), Decimal('100'))

    async def buy() -> None:
        await ledger.apply_fill(_ACCT, OrderSide.BUY, Decimal('0.01'), Decimal('100'), Decimal('0'))

    async def sell() -> None:
        await ledger.apply_fill(_ACCT, OrderSide.SELL, Decimal('0.01'), Decimal('100'), Decimal('0'))

    await asyncio.gather(*[buy() for _ in range(50)], *[sell() for _ in range(50)])

    usdt, btc = await ledger.balance(_ACCT)
    assert usdt == Decimal('100000')
    assert btc == Decimal('100')

    fills = await ledger.fills(_ACCT)
    assert len(fills) == 100
    trade_ids = [int(f.trade_id) for f in fills]
    assert sorted(trade_ids) == list(range(1, 101))


@pytest.mark.asyncio
async def test_fills_do_not_survive_snapshot_round_trip(tmp_path: Path) -> None:

    ledger1 = _new_ledger(tmp_path)
    await ledger1.register_account(_ACCT, Decimal('10000'))
    await ledger1.apply_fill(
        _ACCT, OrderSide.BUY, Decimal('0.12345678'), Decimal('100.50'),
        Decimal('0.01005'), timestamp=_TS,
    )

    ledger2 = _new_ledger(tmp_path)
    await ledger2.load()

    assert await ledger2.fills(_ACCT) == []


@pytest.mark.asyncio
async def test_snapshot_size_stays_bounded_under_fill_growth_only(tmp_path: Path) -> None:

    ledger = _new_ledger(tmp_path)
    snapshot = tmp_path / 'binsim_ledger.json'

    await ledger.register_account(_ACCT, Decimal('100000000'))
    baseline = snapshot.stat().st_size

    for _ in range(100):
        await ledger.apply_fill(
            _ACCT, OrderSide.BUY, Decimal('0.001'), Decimal('100'), Decimal('0'),
        )

    after = snapshot.stat().st_size
    assert after < baseline + _BOUNDED_GROWTH_MARGIN_BYTES


@pytest.mark.asyncio
async def test_apply_order_still_grows_snapshot_via_seen_client_order_ids(tmp_path: Path) -> None:

    ledger = _new_ledger(tmp_path)
    snapshot = tmp_path / 'binsim_ledger.json'

    await ledger.register_account(_ACCT, Decimal('100000000'))
    baseline = snapshot.stat().st_size

    for i in range(100):
        await ledger.apply_order(
            _ACCT, OrderSide.BUY,
            [(Decimal('100'), Decimal('0.001'), Decimal('0'))],
            client_order_id=f'cid-{i:03d}',
        )

    after = snapshot.stat().st_size
    assert after > baseline + _APPLY_ORDER_GROWTH_FLOOR_BYTES


@pytest.mark.asyncio
async def test_snapshot_write_completes_when_caller_cancelled(tmp_path: Path) -> None:

    ledger = _new_ledger(tmp_path)
    await ledger.register_account(_ACCT, Decimal('10000'))

    write_started = threading.Event()
    write_finished = threading.Event()
    original = ledger._write_snapshot_atomic

    def instrumented(payload: dict[str, object]) -> None:

        write_started.set()
        time.sleep(_INSTRUMENTED_WRITE_DELAY_SECONDS)
        original(payload)
        write_finished.set()

    ledger._write_snapshot_atomic = instrumented

    fill_task = asyncio.create_task(
        ledger.apply_fill(
            _ACCT, OrderSide.BUY, Decimal('0.1'), Decimal('100'), Decimal('0'),
        ),
    )

    await asyncio.to_thread(write_started.wait, _WRITE_START_TIMEOUT_SECONDS)
    assert write_started.is_set()

    fill_task.cancel()

    with pytest.raises(asyncio.CancelledError):
        await fill_task

    assert write_finished.is_set()


@pytest.mark.asyncio
async def test_legacy_snapshot_with_fills_field_loads_balances(tmp_path: Path) -> None:

    snapshot = tmp_path / 'binsim_ledger.json'
    legacy = {
        'next_trade_id': 5,
        'next_order_id': 3,
        'accounts': {
            _ACCT: {
                'api_key_hash': 'a' * 64,
                'usdt': '9999',
                'btc': '0.5',
                'fills': [{
                    'trade_id': '1',
                    'side': 'BUY',
                    'qty': '0.5',
                    'price': '100',
                    'fee': '0',
                    'fee_asset': 'USDT',
                    'timestamp': '2024-01-01T00:00:00+00:00',
                }],
                'seen_client_order_ids': ['legacy-coid'],
            },
        },
    }
    snapshot.write_text(json.dumps(legacy))

    ledger = _new_ledger(tmp_path)
    await ledger.load()

    usdt, btc = await ledger.balance(_ACCT)
    assert usdt == Decimal('9999')
    assert btc == Decimal('0.5')
    assert await ledger.fills(_ACCT) == []


@pytest.mark.asyncio
async def test_state_dir_created_if_missing(tmp_path: Path) -> None:

    state_dir = tmp_path / 'nested' / 'binsim_state'
    ledger = Ledger(state_dir)
    await ledger.register_account(_ACCT, Decimal('1'))

    assert state_dir.exists()
    assert (state_dir / 'binsim_ledger.json').exists()


@pytest.mark.asyncio
async def test_apply_order_single_level_buy(tmp_path: Path) -> None:

    ledger = _new_ledger(tmp_path)
    await ledger.register_account(_ACCT, Decimal('10000'))

    order_id, fills = await ledger.apply_order(
        _ACCT, OrderSide.BUY,
        [(Decimal('100'), Decimal('0.1'), Decimal('0.01'))],
        client_order_id='cid-1', timestamp=_TS,
    )

    assert order_id == 1
    assert len(fills) == 1
    assert fills[0].trade_id == '1'
    assert fills[0].qty == Decimal('0.1')

    usdt, btc = await ledger.balance(_ACCT)
    assert usdt == Decimal('10000') - Decimal('10') - Decimal('0.01')
    assert btc == Decimal('0.1')


@pytest.mark.asyncio
async def test_apply_order_walks_multiple_levels(tmp_path: Path) -> None:

    ledger = _new_ledger(tmp_path)
    await ledger.register_account(_ACCT, Decimal('10000'))

    order_id, fills = await ledger.apply_order(
        _ACCT, OrderSide.BUY,
        [
            (Decimal('100'), Decimal('1.0'), Decimal('0.1')),
            (Decimal('101'), Decimal('0.5'), Decimal('0.0505')),
        ],
        client_order_id='cid-1',
    )

    assert order_id == 1
    assert [f.trade_id for f in fills] == ['1', '2']

    usdt, btc = await ledger.balance(_ACCT)
    expected_notional = Decimal('100') + Decimal('50.5')
    expected_fees = Decimal('0.1') + Decimal('0.0505')
    assert usdt == Decimal('10000') - expected_notional - expected_fees
    assert btc == Decimal('1.5')


@pytest.mark.asyncio
async def test_apply_order_sell_credits_usdt_debits_btc(tmp_path: Path) -> None:

    ledger = _new_ledger(tmp_path)
    await ledger.register_account(_ACCT, Decimal('0'), Decimal('1'))

    order_id, fills = await ledger.apply_order(
        _ACCT, OrderSide.SELL,
        [(Decimal('100'), Decimal('0.5'), Decimal('0.05'))],
        client_order_id='cid-1',
    )

    assert order_id == 1
    assert fills[0].side is OrderSide.SELL

    usdt, btc = await ledger.balance(_ACCT)
    assert usdt == Decimal('50') - Decimal('0.05')
    assert btc == Decimal('0.5')


@pytest.mark.asyncio
async def test_apply_order_assigns_monotonic_order_and_trade_ids(tmp_path: Path) -> None:

    ledger = _new_ledger(tmp_path)
    await ledger.register_account(_ACCT, Decimal('10000'), Decimal('1'))

    o1, fs1 = await ledger.apply_order(
        _ACCT, OrderSide.BUY,
        [(Decimal('100'), Decimal('0.1'), Decimal('0'))],
        client_order_id='cid-1',
    )

    o2, fs2 = await ledger.apply_order(
        _ACCT, OrderSide.BUY,
        [
            (Decimal('100'), Decimal('0.1'), Decimal('0')),
            (Decimal('101'), Decimal('0.1'), Decimal('0')),
        ],
        client_order_id='cid-2',
    )

    assert (o1, o2) == (1, 2)
    assert [f.trade_id for f in fs1] == ['1']
    assert [f.trade_id for f in fs2] == ['2', '3']


@pytest.mark.asyncio
async def test_apply_order_rejects_duplicate_client_order_id(tmp_path: Path) -> None:

    ledger = _new_ledger(tmp_path)
    await ledger.register_account(_ACCT, Decimal('10000'))

    await ledger.apply_order(
        _ACCT, OrderSide.BUY,
        [(Decimal('100'), Decimal('0.1'), Decimal('0'))],
        client_order_id='cid-1',
    )

    with pytest.raises(DuplicateClientOrderIdError, match='cid-1'):
        await ledger.apply_order(
            _ACCT, OrderSide.BUY,
            [(Decimal('100'), Decimal('0.1'), Decimal('0'))],
            client_order_id='cid-1',
        )


@pytest.mark.asyncio
async def test_apply_order_duplicate_does_not_mutate_state(tmp_path: Path) -> None:

    ledger = _new_ledger(tmp_path)
    await ledger.register_account(_ACCT, Decimal('10000'))

    await ledger.apply_order(
        _ACCT, OrderSide.BUY,
        [(Decimal('100'), Decimal('0.1'), Decimal('0.01'))],
        client_order_id='cid-1',
    )

    before_usdt, before_btc = await ledger.balance(_ACCT)
    before_fills = await ledger.fills(_ACCT)

    with pytest.raises(DuplicateClientOrderIdError):
        await ledger.apply_order(
            _ACCT, OrderSide.BUY,
            [(Decimal('100'), Decimal('0.1'), Decimal('0.01'))],
            client_order_id='cid-1',
        )

    after_usdt, after_btc = await ledger.balance(_ACCT)
    after_fills = await ledger.fills(_ACCT)

    assert (after_usdt, after_btc) == (before_usdt, before_btc)
    assert len(after_fills) == len(before_fills)


@pytest.mark.asyncio
async def test_apply_order_rejects_empty_fills(tmp_path: Path) -> None:

    ledger = _new_ledger(tmp_path)
    await ledger.register_account(_ACCT, Decimal('10000'))

    with pytest.raises(ValueError, match='fills cannot be empty'):
        await ledger.apply_order(_ACCT, OrderSide.BUY, [], client_order_id='cid-1')


@pytest.mark.asyncio
async def test_apply_order_rejects_empty_client_order_id(tmp_path: Path) -> None:

    ledger = _new_ledger(tmp_path)
    await ledger.register_account(_ACCT, Decimal('10000'))

    with pytest.raises(ValueError, match='client_order_id cannot be empty'):
        await ledger.apply_order(
            _ACCT, OrderSide.BUY,
            [(Decimal('100'), Decimal('0.1'), Decimal('0'))],
            client_order_id='',
        )


@pytest.mark.asyncio
async def test_apply_order_rejects_unknown_account(tmp_path: Path) -> None:

    ledger = _new_ledger(tmp_path)

    with pytest.raises(KeyError, match='not registered'):
        await ledger.apply_order(
            _ACCT, OrderSide.BUY,
            [(Decimal('100'), Decimal('0.1'), Decimal('0'))],
            client_order_id='cid-1',
        )


@pytest.mark.asyncio
async def test_apply_order_buy_raises_when_insufficient_usdt(tmp_path: Path) -> None:

    ledger = _new_ledger(tmp_path)
    await ledger.register_account(_ACCT, Decimal('5'))

    with pytest.raises(InsufficientBalanceError, match='USDT would be'):
        await ledger.apply_order(
            _ACCT, OrderSide.BUY,
            [(Decimal('100'), Decimal('0.1'), Decimal('0'))],
            client_order_id='cid-1',
        )


@pytest.mark.asyncio
async def test_apply_order_sell_raises_when_insufficient_btc(tmp_path: Path) -> None:

    ledger = _new_ledger(tmp_path)
    await ledger.register_account(_ACCT, Decimal('0'), Decimal('0.05'))

    with pytest.raises(InsufficientBalanceError, match='BTC would be'):
        await ledger.apply_order(
            _ACCT, OrderSide.SELL,
            [(Decimal('100'), Decimal('0.1'), Decimal('0'))],
            client_order_id='cid-1',
        )


@pytest.mark.asyncio
async def test_apply_order_aggregates_balance_check_across_levels(tmp_path: Path) -> None:

    ledger = _new_ledger(tmp_path)
    await ledger.register_account(_ACCT, Decimal('15'))

    with pytest.raises(InsufficientBalanceError, match='USDT would be'):
        await ledger.apply_order(
            _ACCT, OrderSide.BUY,
            [
                (Decimal('100'), Decimal('0.1'), Decimal('0')),
                (Decimal('101'), Decimal('0.1'), Decimal('0')),
            ],
            client_order_id='cid-1',
        )


@pytest.mark.asyncio
async def test_apply_order_includes_per_level_fees_in_balance(tmp_path: Path) -> None:

    ledger = _new_ledger(tmp_path)
    await ledger.register_account(_ACCT, Decimal('10.10'))

    with pytest.raises(InsufficientBalanceError, match='USDT would be'):
        await ledger.apply_order(
            _ACCT, OrderSide.BUY,
            [(Decimal('100'), Decimal('0.1'), Decimal('0.20'))],
            client_order_id='cid-1',
        )


@pytest.mark.asyncio
async def test_apply_order_rejects_non_positive_price(tmp_path: Path) -> None:

    ledger = _new_ledger(tmp_path)
    await ledger.register_account(_ACCT, Decimal('10000'))

    with pytest.raises(ValueError, match='price must be positive'):
        await ledger.apply_order(
            _ACCT, OrderSide.BUY,
            [(Decimal('0'), Decimal('0.1'), Decimal('0'))],
            client_order_id='cid-1',
        )


@pytest.mark.asyncio
async def test_apply_order_rejects_non_positive_qty(tmp_path: Path) -> None:

    ledger = _new_ledger(tmp_path)
    await ledger.register_account(_ACCT, Decimal('10000'))

    with pytest.raises(ValueError, match='qty must be positive'):
        await ledger.apply_order(
            _ACCT, OrderSide.BUY,
            [(Decimal('100'), Decimal('0'), Decimal('0'))],
            client_order_id='cid-1',
        )


@pytest.mark.asyncio
async def test_apply_order_rejects_negative_fee(tmp_path: Path) -> None:

    ledger = _new_ledger(tmp_path)
    await ledger.register_account(_ACCT, Decimal('10000'))

    with pytest.raises(ValueError, match='fee must be non-negative'):
        await ledger.apply_order(
            _ACCT, OrderSide.BUY,
            [(Decimal('100'), Decimal('0.1'), Decimal('-0.01'))],
            client_order_id='cid-1',
        )


@pytest.mark.asyncio
async def test_apply_order_persists_client_order_ids_through_restart(tmp_path: Path) -> None:

    ledger1 = _new_ledger(tmp_path)
    await ledger1.register_account(_ACCT, Decimal('10000'))
    await ledger1.apply_order(
        _ACCT, OrderSide.BUY,
        [(Decimal('100'), Decimal('0.1'), Decimal('0'))],
        client_order_id='cid-1',
    )

    ledger2 = _new_ledger(tmp_path)
    await ledger2.load()

    with pytest.raises(DuplicateClientOrderIdError, match='cid-1'):
        await ledger2.apply_order(
            _ACCT, OrderSide.BUY,
            [(Decimal('100'), Decimal('0.1'), Decimal('0'))],
            client_order_id='cid-1',
        )


@pytest.mark.asyncio
async def test_apply_order_after_restart_continues_monotonic_order_id(tmp_path: Path) -> None:

    ledger1 = _new_ledger(tmp_path)
    await ledger1.register_account(_ACCT, Decimal('10000'))
    o1, _ = await ledger1.apply_order(
        _ACCT, OrderSide.BUY,
        [(Decimal('100'), Decimal('0.1'), Decimal('0'))],
        client_order_id='cid-1',
    )

    ledger2 = _new_ledger(tmp_path)
    await ledger2.load()
    o2, _ = await ledger2.apply_order(
        _ACCT, OrderSide.BUY,
        [(Decimal('100'), Decimal('0.1'), Decimal('0'))],
        client_order_id='cid-2',
    )

    assert o2 == o1 + 1


@pytest.mark.asyncio
async def test_register_account_returns_64_hex_api_key(tmp_path: Path) -> None:

    ledger = _new_ledger(tmp_path)
    api_key = await ledger.register_account(_ACCT, Decimal('1'))

    assert isinstance(api_key, str)
    assert len(api_key) == 64
    assert all(c in '0123456789abcdef' for c in api_key)


@pytest.mark.asyncio
async def test_register_account_yields_distinct_keys_for_distinct_accounts(
    tmp_path: Path,
) -> None:

    ledger = _new_ledger(tmp_path)
    k1 = await ledger.register_account('a', Decimal('1'))
    k2 = await ledger.register_account('b', Decimal('1'))
    k3 = await ledger.register_account('c', Decimal('1'))

    assert len({k1, k2, k3}) == 3


@pytest.mark.asyncio
async def test_account_for_api_key_resolves_registered_key(tmp_path: Path) -> None:

    ledger = _new_ledger(tmp_path)
    api_key = await ledger.register_account(_ACCT, Decimal('1'))

    assert ledger.account_for_api_key(api_key) == _ACCT


@pytest.mark.asyncio
async def test_account_for_api_key_returns_none_for_unknown(tmp_path: Path) -> None:

    ledger = _new_ledger(tmp_path)
    await ledger.register_account(_ACCT, Decimal('1'))

    assert ledger.account_for_api_key('not-a-real-key') is None


@pytest.mark.asyncio
async def test_api_key_index_survives_load(tmp_path: Path) -> None:

    ledger1 = _new_ledger(tmp_path)
    api_key = await ledger1.register_account(_ACCT, Decimal('10000'))

    ledger2 = _new_ledger(tmp_path)
    await ledger2.load()

    assert ledger2.account_for_api_key(api_key) == _ACCT


@pytest.mark.asyncio
async def test_snapshot_persists_api_key_hash_not_plaintext(tmp_path: Path) -> None:
    import hashlib

    ledger = _new_ledger(tmp_path)
    api_key = await ledger.register_account(_ACCT, Decimal('10000'))

    snapshot = json.loads((tmp_path / 'binsim_ledger.json').read_text())
    persisted = snapshot['accounts'][_ACCT]

    assert 'api_key' not in persisted
    expected = hashlib.sha256(api_key.encode('utf-8')).hexdigest()  # lgtm[py/weak-sensitive-data-hashing]
    assert persisted['api_key_hash'] == expected
    assert api_key not in (tmp_path / 'binsim_ledger.json').read_text()


@pytest.mark.asyncio
async def test_register_account_rejects_whitespace_account_id(tmp_path: Path) -> None:
    ledger = _new_ledger(tmp_path)

    with pytest.raises(ValueError, match='account_id cannot be empty or whitespace-only'):
        await ledger.register_account('   ', Decimal('1'))


@pytest.mark.asyncio
async def test_register_account_strips_account_id(tmp_path: Path) -> None:
    ledger = _new_ledger(tmp_path)
    await ledger.register_account('  acc-stripped  ', Decimal('10000'))

    accounts = await ledger.accounts()
    assert accounts == ['acc-stripped']


@pytest.mark.asyncio
async def test_apply_order_rejects_whitespace_client_order_id(tmp_path: Path) -> None:
    ledger = _new_ledger(tmp_path)
    await ledger.register_account(_ACCT, Decimal('10000'))

    with pytest.raises(ValueError, match='client_order_id cannot be empty or whitespace-only'):
        await ledger.apply_order(
            _ACCT, OrderSide.BUY,
            [(Decimal('100'), Decimal('0.1'), Decimal('0'))],
            client_order_id='   ',
        )


@pytest.mark.asyncio
async def test_apply_order_strips_client_order_id_for_dedup(tmp_path: Path) -> None:
    ledger = _new_ledger(tmp_path)
    await ledger.register_account(_ACCT, Decimal('10000'))

    await ledger.apply_order(
        _ACCT, OrderSide.BUY,
        [(Decimal('100'), Decimal('0.1'), Decimal('0'))],
        client_order_id='  cid-1  ',
    )

    with pytest.raises(DuplicateClientOrderIdError, match='cid-1'):
        await ledger.apply_order(
            _ACCT, OrderSide.BUY,
            [(Decimal('100'), Decimal('0.1'), Decimal('0'))],
            client_order_id='cid-1',
        )


@pytest.mark.asyncio
@pytest.mark.parametrize('field', ['qty', 'price', 'fee'])
async def test_apply_fill_rejects_non_finite(tmp_path: Path, field: str) -> None:
    ledger = _new_ledger(tmp_path)
    await ledger.register_account(_ACCT, Decimal('10000'))

    args = {'qty': Decimal('0.1'), 'price': Decimal('100'), 'fee': Decimal('0')}
    args[field] = Decimal('NaN')

    with pytest.raises(ValueError, match='must all be finite'):
        await ledger.apply_fill(
            _ACCT, OrderSide.BUY,
            args['qty'], args['price'], args['fee'],
        )


@pytest.mark.asyncio
@pytest.mark.parametrize('field_index', [0, 1, 2])
async def test_apply_order_rejects_non_finite_in_level(tmp_path: Path, field_index: int) -> None:
    ledger = _new_ledger(tmp_path)
    await ledger.register_account(_ACCT, Decimal('10000'))

    level = [Decimal('100'), Decimal('0.1'), Decimal('0')]
    level[field_index] = Decimal('Infinity')

    with pytest.raises(ValueError, match='must have finite'):
        await ledger.apply_order(
            _ACCT, OrderSide.BUY,
            [(level[0], level[1], level[2])],
            client_order_id='cid-1',
        )


@pytest.mark.asyncio
@pytest.mark.parametrize('field', ['initial_usdt', 'initial_btc'])
async def test_register_account_rejects_non_finite_initial_balance(tmp_path: Path, field: str) -> None:
    ledger = _new_ledger(tmp_path)
    args = {'initial_usdt': Decimal('10000'), 'initial_btc': Decimal('0')}
    args[field] = Decimal('NaN')

    with pytest.raises(ValueError, match='initial balances must be finite'):
        await ledger.register_account(_ACCT, args['initial_usdt'], args['initial_btc'])
