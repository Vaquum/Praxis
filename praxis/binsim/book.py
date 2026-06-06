'''Top-of-book snapshot replaced wholesale from a poll-driven source.'''

from __future__ import annotations

from decimal import Decimal

from praxis.core.domain.enums import OrderSide


__all__ = ['OrderBook']


class OrderBook:

    '''Single-symbol top-N snapshot for market-order fill simulation.

    The book is replaced wholesale via `replace()` whenever the upstream
    depth poller receives a fresh snapshot. There is no snapshot+diff
    dance — the hosted source hands the full top-N each poll.

    `consume_qty_for_market_order()` is non-mutating: it walks the
    snapshot and returns the fill ladder. Successive consumes within a
    poll window see the same book (no in-window liquidity decay — that
    is acceptable for MMVP, and the 1000ms poll cadence is the model's
    effective price discretization).
    '''

    def __init__(self) -> None:

        self._bids: list[tuple[Decimal, Decimal]] = []
        self._asks: list[tuple[Decimal, Decimal]] = []
        self._last_update_id: int = 0
        self._ts_ms: int = 0

    @property
    def last_update_id(self) -> int:

        return self._last_update_id

    @property
    def ts_ms(self) -> int:

        return self._ts_ms

    @property
    def bids(self) -> list[tuple[Decimal, Decimal]]:

        return list(self._bids)

    @property
    def asks(self) -> list[tuple[Decimal, Decimal]]:

        return list(self._asks)

    def replace(
        self,
        bids: list[tuple[Decimal, Decimal]],
        asks: list[tuple[Decimal, Decimal]],
        last_update_id: int,
        ts_ms: int,
    ) -> None:

        '''Replace the book with a new top-N snapshot.

        Args:
            bids: (price, qty) tuples, strictly descending by price (best bid at index 0).
            asks: (price, qty) tuples, strictly ascending by price (best ask at index 0).
            last_update_id: monotonic identifier from the upstream source.
            ts_ms: source-side unix-ms timestamp from the upstream source.

        Raises:
            ValueError: any of bids/asks empty, non-positive price/qty, mis-sorted, crossed, or last_update_id moved backwards.
        '''

        if not bids:
            raise ValueError('bids cannot be empty')

        if not asks:
            raise ValueError('asks cannot be empty')

        for price, qty in bids:
            if not price.is_finite() or not qty.is_finite():
                raise ValueError(f'bid level must be finite: ({price}, {qty})')
            if price <= 0 or qty <= 0:
                raise ValueError(f'bid level has non-positive value: ({price}, {qty})')

        for price, qty in asks:
            if not price.is_finite() or not qty.is_finite():
                raise ValueError(f'ask level must be finite: ({price}, {qty})')
            if price <= 0 or qty <= 0:
                raise ValueError(f'ask level has non-positive value: ({price}, {qty})')

        for i in range(1, len(bids)):
            if bids[i][0] >= bids[i - 1][0]:
                raise ValueError(
                    f'bids must be strictly descending; level {i} price {bids[i][0]} >= level {i-1} price {bids[i-1][0]}'
                )

        for i in range(1, len(asks)):
            if asks[i][0] <= asks[i - 1][0]:
                raise ValueError(
                    f'asks must be strictly ascending; level {i} price {asks[i][0]} <= level {i-1} price {asks[i-1][0]}'
                )

        if bids[0][0] >= asks[0][0]:
            raise ValueError(
                f'book is crossed: best bid {bids[0][0]} >= best ask {asks[0][0]}'
            )

        if last_update_id < self._last_update_id:
            raise ValueError(
                f'last_update_id moved backwards: {last_update_id} < {self._last_update_id}'
            )

        self._bids = list(bids)
        self._asks = list(asks)
        self._last_update_id = last_update_id
        self._ts_ms = ts_ms

    def consume_qty_for_market_order(
        self,
        side: OrderSide,
        qty: Decimal,
    ) -> list[tuple[Decimal, Decimal]]:

        '''Walk the book to compute the fill ladder for a market order.

        Args:
            side: `BUY` consumes from asks, `SELL` consumes from bids.
            qty: base-asset quantity requested.

        Returns:
            (price, fill_qty) tuples in walk order. The summed
            fill_qty may be less than `qty` if the visible book is
            exhausted — the caller decides whether that constitutes
            a partial fill or a rejection.

        Raises:
            ValueError: qty is non-positive.
            RuntimeError: the relevant side of the book is empty
                (no snapshot loaded yet).
        '''

        if not qty.is_finite():
            raise ValueError(f'qty must be finite, got {qty}')

        if qty <= 0:
            raise ValueError(f'qty must be positive, got {qty}')

        levels = self._asks if side is OrderSide.BUY else self._bids

        if not levels:
            raise RuntimeError('order book is empty; call replace() first')

        fills: list[tuple[Decimal, Decimal]] = []
        remaining = qty

        for price, level_qty in levels:
            if remaining <= 0:
                break

            take = level_qty if level_qty <= remaining else remaining
            fills.append((price, take))
            remaining -= take

        return fills

    def consume_quote_for_market_buy(
        self,
        quote_qty: Decimal,
    ) -> list[tuple[Decimal, Decimal]]:

        '''Walk the asks until quote-asset spend is exhausted.

        Mirrors Binance's MARKET BUY with `quoteOrderQty`: the venue
        walks the ask ladder consuming each level up to the remaining
        quote budget, partial-taking the last level to land exactly on
        `quote_qty` spend.

        Args:
            quote_qty: quote-asset budget (positive Decimal).

        Returns:
            (price, fill_qty) tuples in walk order. The summed
            `price * fill_qty` may be less than `quote_qty` if the
            visible book is exhausted.

        Raises:
            ValueError: `quote_qty` is non-positive.
            RuntimeError: the ask side of the book is empty.
        '''

        if not quote_qty.is_finite():
            raise ValueError(f'quote_qty must be finite, got {quote_qty}')

        if quote_qty <= 0:
            raise ValueError(f'quote_qty must be positive, got {quote_qty}')

        if not self._asks:
            raise RuntimeError('order book is empty; call replace() first')

        fills: list[tuple[Decimal, Decimal]] = []
        remaining_quote = quote_qty

        for price, level_qty in self._asks:
            if remaining_quote <= 0:
                break

            level_quote_cap = price * level_qty
            if level_quote_cap <= remaining_quote:
                fills.append((price, level_qty))
                remaining_quote -= level_quote_cap
            else:
                take_base = remaining_quote / price
                fills.append((price, take_base))
                remaining_quote = Decimal('0')

        return fills
