from __future__ import annotations

from datetime import datetime, UTC
from decimal import Decimal

import pytest

from praxis.core.domain.enums import OrderSide, OrderStatus, OrderType
from praxis.infrastructure.secret_store import Credentials
from praxis.infrastructure.venue_adapter import (
    NotFoundError,
    OrderRejectedError,
    SymbolFilters,
    VenueAdapter,
)
from praxis.replay.replay_venue_adapter import ReplayVenueAdapter

_SYMBOL = 'BTCUSDT'
_ACCT = 'acc-1'
_FILL_PRICE = Decimal('60000')


def _filters() -> dict[str, SymbolFilters]:
    return {
        _SYMBOL: SymbolFilters(
            symbol=_SYMBOL,
            tick_size=Decimal('0.01'),
            lot_step=Decimal('0.00001'),
            lot_min=Decimal('0.00001'),
            lot_max=Decimal('9000'),
            min_notional=Decimal('10'),
        ),
    }


def _clock() -> datetime:
    return datetime(2026, 1, 1, tzinfo=UTC)


def _make_adapter(quote: str = '100000') -> ReplayVenueAdapter:
    adapter = ReplayVenueAdapter(
        clock=_clock,
        filters=_filters(),
        starting_balances={'USDT': Decimal(quote)},
    )
    adapter.set_price(_FILL_PRICE)
    adapter.register_account(_ACCT, Credentials(api_key='k', api_secret='s'))
    return adapter


def test_conforms_to_protocol() -> None:
    assert isinstance(_make_adapter(), VenueAdapter)


@pytest.mark.asyncio
async def test_quote_native_buy_fills_at_price() -> None:
    adapter = _make_adapter()

    result = await adapter.submit_order(
        _ACCT, _SYMBOL, OrderSide.BUY, OrderType.MARKET, None,
        quote_qty=Decimal('6000'), client_order_id='coid-buy',
    )

    assert result.status is OrderStatus.FILLED
    assert len(result.immediate_fills) == 1
    fill = result.immediate_fills[0]
    assert fill.price == _FILL_PRICE
    assert fill.qty == Decimal('0.1')
    assert fill.fee == Decimal('6')
    assert fill.fee_asset == 'USDT'
    assert fill.is_maker is False


@pytest.mark.asyncio
async def test_buy_then_sell_settles_balances() -> None:
    adapter = _make_adapter()

    await adapter.submit_order(
        _ACCT, _SYMBOL, OrderSide.BUY, OrderType.MARKET, None,
        quote_qty=Decimal('6000'), client_order_id='coid-buy',
    )
    balances = {b.asset: b.free for b in await adapter.query_balance(
        _ACCT, frozenset({'USDT', 'BTC'}),
    )}

    assert balances['BTC'] == Decimal('0.1')
    assert balances['USDT'] == Decimal('93994')

    await adapter.submit_order(
        _ACCT, _SYMBOL, OrderSide.SELL, OrderType.MARKET, Decimal('0.1'),
        client_order_id='coid-sell',
    )
    after = {b.asset: b.free for b in await adapter.query_balance(
        _ACCT, frozenset({'USDT', 'BTC'}),
    )}

    assert after['BTC'] == Decimal('0E-8') or after['BTC'] == Decimal('0')
    assert after['USDT'] == Decimal('99988')


@pytest.mark.asyncio
async def test_query_trades_honors_from_id() -> None:
    adapter = _make_adapter()

    await adapter.submit_order(
        _ACCT, _SYMBOL, OrderSide.BUY, OrderType.MARKET, None,
        quote_qty=Decimal('6000'), client_order_id='coid-1',
    )
    await adapter.submit_order(
        _ACCT, _SYMBOL, OrderSide.SELL, OrderType.MARKET, Decimal('0.05'),
        client_order_id='coid-2',
    )

    all_trades = await adapter.query_trades(_ACCT, _SYMBOL)
    seqs = sorted(int(t.venue_trade_id.rsplit('-', 1)[1]) for t in all_trades)
    assert len(seqs) == 2

    filtered = await adapter.query_trades(_ACCT, _SYMBOL, from_id=seqs[1])
    assert len(filtered) == 1
    assert int(filtered[0].venue_trade_id.rsplit('-', 1)[1]) == seqs[1]


@pytest.mark.asyncio
async def test_submit_without_price_rejected() -> None:
    adapter = ReplayVenueAdapter(clock=_clock, filters=_filters())
    adapter.register_account(_ACCT, Credentials(api_key='k', api_secret='s'))

    with pytest.raises(OrderRejectedError, match='no current price'):
        await adapter.submit_order(
            _ACCT, _SYMBOL, OrderSide.BUY, OrderType.MARKET, None,
            quote_qty=Decimal('6000'),
        )


@pytest.mark.asyncio
async def test_non_market_order_rejected() -> None:
    adapter = _make_adapter()

    with pytest.raises(OrderRejectedError, match='MARKET only'):
        await adapter.submit_order(
            _ACCT, _SYMBOL, OrderSide.BUY, OrderType.LIMIT, Decimal('0.1'),
            price=_FILL_PRICE,
        )


@pytest.mark.asyncio
async def test_qty_and_quote_qty_rejected() -> None:
    adapter = _make_adapter()

    with pytest.raises(OrderRejectedError, match='mutually exclusive'):
        await adapter.submit_order(
            _ACCT, _SYMBOL, OrderSide.BUY, OrderType.MARKET, Decimal('0.1'),
            quote_qty=Decimal('6000'),
        )


@pytest.mark.asyncio
async def test_quote_qty_sell_rejected() -> None:
    adapter = _make_adapter()

    with pytest.raises(OrderRejectedError, match='MARKET BUY'):
        await adapter.submit_order(
            _ACCT, _SYMBOL, OrderSide.SELL, OrderType.MARKET, None,
            quote_qty=Decimal('6000'),
        )


@pytest.mark.asyncio
async def test_insufficient_quote_balance_rejected() -> None:
    adapter = _make_adapter(quote='10')

    with pytest.raises(OrderRejectedError, match='insufficient USDT'):
        await adapter.submit_order(
            _ACCT, _SYMBOL, OrderSide.BUY, OrderType.MARKET, None,
            quote_qty=Decimal('6000'),
        )


def test_quantize_floor_snaps() -> None:
    adapter = _make_adapter()

    result = adapter.quantize_for_command(
        _SYMBOL, Decimal('0.123456789'), OrderType.MARKET,
    )

    assert result.rejection_reason is None
    assert result.snapped_qty == Decimal('0.12345')


def test_quantize_below_min_qty_rejected() -> None:
    adapter = _make_adapter()

    result = adapter.quantize_for_command(
        _SYMBOL, Decimal('0.000001'), OrderType.MARKET,
    )

    assert result.snapped_qty is None
    assert result.rejection_reason == 'INTAKE_BELOW_MIN_QTY'


def test_quantize_below_min_notional_rejected() -> None:
    adapter = _make_adapter()

    result = adapter.quantize_for_command(
        _SYMBOL, Decimal('0.0001'), OrderType.MARKET,
        reference_price=Decimal('1'),
    )

    assert result.snapped_qty is None
    assert result.rejection_reason == 'INTAKE_BELOW_MIN_NOTIONAL'


@pytest.mark.asyncio
async def test_no_open_orders_and_cancel_raises() -> None:
    adapter = _make_adapter()
    await adapter.submit_order(
        _ACCT, _SYMBOL, OrderSide.BUY, OrderType.MARKET, None,
        quote_qty=Decimal('6000'), client_order_id='coid-buy',
    )

    assert await adapter.query_open_orders(_ACCT, _SYMBOL) == []

    with pytest.raises(NotFoundError):
        await adapter.cancel_order(_ACCT, _SYMBOL, client_order_id='coid-buy')


@pytest.mark.asyncio
async def test_query_order_returns_recorded_fill() -> None:
    adapter = _make_adapter()
    await adapter.submit_order(
        _ACCT, _SYMBOL, OrderSide.BUY, OrderType.MARKET, None,
        quote_qty=Decimal('6000'), client_order_id='coid-buy',
    )

    order = await adapter.query_order(_ACCT, _SYMBOL, client_order_id='coid-buy')

    assert order.status is OrderStatus.FILLED
    assert order.filled_qty == Decimal('0.1')
