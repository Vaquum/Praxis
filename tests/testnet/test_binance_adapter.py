'''Verify BinanceAdapter against the Binance Spot testnet.'''

from __future__ import annotations

import os
from decimal import Decimal, ROUND_CEILING

import aiohttp
import pytest

from praxis.core.domain.enums import OrderSide, OrderStatus, OrderType
from praxis.infrastructure.binance_adapter import BinanceAdapter
from tests.testnet.conftest import (
    HTTP_OK,
    MIN_ORDER_QUOTE_QTY,
    REST_BASE,
    SESSION_TIMEOUT,
    SYMBOL,
    pytestmark,
    skip_no_creds,
)

__all__ = ['pytestmark']

_ACCOUNT_ID = 'testnet'
_PRICE_MULTIPLIER = Decimal('0.6')
_QTY_STEP = Decimal('0.00001')
_PRICE_STEP = Decimal('0.01')


def _credentials() -> dict[str, tuple[str, str]]:

    '''
    Fetch testnet API credentials from the environment.

    Returns:
        dict[str, tuple[str, str]]: Mapping of account_id to (key, secret)
    '''

    return {
        _ACCOUNT_ID: (
            os.environ['BINANCE_TESTNET_API_KEY'],
            os.environ['BINANCE_TESTNET_API_SECRET'],
        ),
    }


async def _current_price() -> Decimal:

    '''
    Fetch the current BTCUSDT price from the testnet ticker.

    Returns:
        Decimal: Current market price
    '''

    async with (
        aiohttp.ClientSession(timeout=SESSION_TIMEOUT) as s,
        s.get(
            f"{REST_BASE}/api/v3/ticker/price",
            params={'symbol': SYMBOL},
        ) as r,
    ):
        assert r.status == HTTP_OK
        data = await r.json()
    return Decimal(data['price'])


def _min_qty(price: Decimal) -> Decimal:

    '''
    Compute the minimum order quantity to exceed MIN_NOTIONAL at a given price.

    Args:
        price (Decimal): Price per unit

    Returns:
        Decimal: Minimum quantity rounded up to lot step size
    '''

    raw = Decimal(MIN_ORDER_QUOTE_QTY) / price
    return raw.quantize(_QTY_STEP, rounding=ROUND_CEILING)


@skip_no_creds
@pytest.mark.asyncio
async def test_market_buy_filled() -> None:

    '''Verify market buy fills immediately with non-empty fills.'''

    price = await _current_price()
    qty = _min_qty(price)

    async with BinanceAdapter(REST_BASE, _credentials()) as adapter:
        result = await adapter.submit_order(
            account_id=_ACCOUNT_ID,
            symbol=SYMBOL,
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            qty=qty,
        )

    assert result.status == OrderStatus.FILLED
    assert len(result.immediate_fills) > 0
    assert result.venue_order_id


@skip_no_creds
@pytest.mark.asyncio
async def test_limit_buy_rests_at_far_below_price() -> None:

    '''Verify limit buy at far-below price rests as OPEN with no fills.'''

    price = await _current_price()
    far_below = (price * _PRICE_MULTIPLIER).quantize(_PRICE_STEP)
    qty = _min_qty(far_below)

    async with BinanceAdapter(REST_BASE, _credentials()) as adapter:
        result = await adapter.submit_order(
            account_id=_ACCOUNT_ID,
            symbol=SYMBOL,
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            qty=qty,
            price=far_below,
        )

    assert result.status == OrderStatus.OPEN
    assert len(result.immediate_fills) == 0
    assert result.venue_order_id


@skip_no_creds
@pytest.mark.asyncio
async def test_limit_ioc_expires_at_far_below_price() -> None:

    '''Verify limit IOC at far-below price expires immediately with no fills.'''

    price = await _current_price()
    far_below = (price * _PRICE_MULTIPLIER).quantize(_PRICE_STEP)
    qty = _min_qty(far_below)

    async with BinanceAdapter(REST_BASE, _credentials()) as adapter:
        result = await adapter.submit_order(
            account_id=_ACCOUNT_ID,
            symbol=SYMBOL,
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT_IOC,
            qty=qty,
            price=far_below,
        )

    assert result.status == OrderStatus.EXPIRED
    assert len(result.immediate_fills) == 0
    assert result.venue_order_id
