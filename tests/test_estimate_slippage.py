from __future__ import annotations

import logging
from decimal import Decimal

import pytest

from praxis.core.domain.enums import OrderSide
from praxis.core.estimate_slippage import estimate_slippage
from praxis.infrastructure.venue_adapter import OrderBookLevel, OrderBookSnapshot


def test_estimate_slippage_buy_walks_ask_levels() -> None:
    book = OrderBookSnapshot(
        bids=(OrderBookLevel(price=Decimal('100'), qty=Decimal('5')),),
        asks=(
            OrderBookLevel(price=Decimal('101'), qty=Decimal('1')),
            OrderBookLevel(price=Decimal('102'), qty=Decimal('2')),
        ),
        last_update_id=1,
    )

    result = estimate_slippage(book, qty=Decimal('2'), side=OrderSide.BUY)

    assert result is not None
    assert result.mid_price == Decimal('100.5')
    assert result.simulated_vwap == Decimal('101.5')
    assert result.slippage_estimate_bps == Decimal('99.50248756218905472636815920')


def test_estimate_slippage_sell_walks_bid_levels() -> None:
    book = OrderBookSnapshot(
        bids=(
            OrderBookLevel(price=Decimal('99'), qty=Decimal('1')),
            OrderBookLevel(price=Decimal('98'), qty=Decimal('2')),
        ),
        asks=(OrderBookLevel(price=Decimal('101'), qty=Decimal('5')),),
        last_update_id=1,
    )

    result = estimate_slippage(book, qty=Decimal('2'), side=OrderSide.SELL)

    assert result is not None
    assert result.mid_price == Decimal('100')
    assert result.simulated_vwap == Decimal('98.5')
    assert result.slippage_estimate_bps == Decimal('-150.000')


def test_estimate_slippage_returns_none_when_book_side_missing() -> None:
    book = OrderBookSnapshot(
        bids=(),
        asks=(OrderBookLevel(price=Decimal('101'), qty=Decimal('5')),),
        last_update_id=1,
    )

    result = estimate_slippage(book, qty=Decimal('1'), side=OrderSide.BUY)

    assert result is None


def test_estimate_slippage_partial_depth_logs_warning(
    caplog: pytest.LogCaptureFixture,
) -> None:
    book = OrderBookSnapshot(
        bids=(OrderBookLevel(price=Decimal('100'), qty=Decimal('5')),),
        asks=(OrderBookLevel(price=Decimal('101'), qty=Decimal('1')),),
        last_update_id=1,
    )

    with caplog.at_level(logging.WARNING):
        result = estimate_slippage(book, qty=Decimal('2'), side=OrderSide.BUY)

    assert result is not None
    assert result.simulated_vwap == Decimal('101')
    messages = [r.message for r in caplog.records]
    assert any('book depth insufficient:' in message for message in messages)
