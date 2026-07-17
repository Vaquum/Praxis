'''In-process simulated venue for replay runs.

Implements the `VenueAdapter` protocol with deterministic market-order
fills at the current replayed bar price. A replay run constructs one
`ReplayVenueAdapter`, hands it to `Trading(venue_adapter=...)`, and the
driver calls `set_price` before dispatching each bar so ENTER/EXIT
orders fill at that bar's close. There is no network, no WebSocket
stream, and no resting-order book: every market order fills fully and
immediately and is returned via `SubmitResult.immediate_fills`, which
is the same fill path the live adapter feeds.

Fees match the binsim paper venue: a taker fee of `fee_rate * notional`
debited in the quote asset (USDT), so a replay run and a paper run book
the same costs.
'''

from __future__ import annotations

import logging
from collections.abc import Callable, Sequence
from datetime import datetime
from decimal import Decimal
from typing import Any

from praxis.core.domain.enums import OrderSide, OrderStatus, OrderType
from praxis.core.domain.health_snapshot import HealthSnapshot
from praxis.infrastructure.secret_store import Credentials
from praxis.infrastructure.venue_adapter import (
    ApiPermissions,
    BalanceEntry,
    CancelResult,
    CommandQuantization,
    ExecutionReport,
    ImmediateFill,
    NotFoundError,
    OrderBookLevel,
    OrderBookSnapshot,
    OrderRejectedError,
    SubmitResult,
    SymbolFilters,
    VenueOrder,
    VenueTrade,
)

__all__ = ['ReplayVenueAdapter']

_log = logging.getLogger(__name__)

_QUOTE_ASSET = 'USDT'
_TAKER_FEE_RATE = Decimal('0.001')
_FILTER_REJECT_CODE = -1013
_ZERO = Decimal(0)
_REJECT_BELOW_MIN_QTY = 'INTAKE_BELOW_MIN_QTY'
_REJECT_BELOW_MIN_NOTIONAL = 'INTAKE_BELOW_MIN_NOTIONAL'
_MS_PER_SECOND = 1000


def _replay_trade_seq(venue_trade_id: str) -> int:
    '''Parse the monotonic sequence from a replay venue trade id (`rv-t-{seq}`).'''

    return int(venue_trade_id.rsplit('-', 1)[1])


class ReplayVenueAdapter:
    '''Deterministic market-fill venue driven by a per-bar price cursor.

    Args:
        clock: Source of the current simulated UTC time for fill and
            trade timestamps; the replay run injects `ReplayClock.now`.
        filters: Per-symbol venue filters, keyed by symbol, used for
            lot-size snapping and notional gating.
        starting_balances: Initial free balances per asset applied to
            every registered account. Defaults to an empty book.
        fee_rate: Taker fee fraction of notional, debited in the quote
            asset. Defaults to the binsim paper rate.
    '''

    def __init__(
        self,
        *,
        clock: Callable[[], datetime],
        filters: dict[str, SymbolFilters],
        starting_balances: dict[str, Decimal] | None = None,
        fee_rate: Decimal = _TAKER_FEE_RATE,
    ) -> None:
        '''Store the price cursor, filters, and starting balances.'''

        self._clock = clock
        self._filters = dict(filters)
        self._starting_balances = dict(starting_balances or {})
        self._fee_rate = fee_rate
        self._current_price: Decimal | None = None
        self._accounts: dict[str, dict[str, Decimal]] = {}
        self._orders: dict[str, VenueOrder] = {}
        self._trades: dict[str, list[VenueTrade]] = {}
        self._seq = 0

    def set_price(self, price: Decimal) -> None:
        '''Set the fill price for subsequent orders to the bar's close.

        Args:
            price: The current replayed bar's close price.
        '''

        if not price.is_finite() or price <= _ZERO:
            msg = f'replay price must be a positive finite Decimal, got {price}'
            raise ValueError(msg)

        self._current_price = price

    def register_account(self, account_id: str, credentials: Credentials) -> None:
        '''Open a balance book for an account seeded with starting balances.'''

        self._accounts[account_id] = dict(self._starting_balances)

    def unregister_account(self, account_id: str) -> None:
        '''Drop an account's balance book.'''

        del self._accounts[account_id]

    async def query_api_permissions(self, account_id: str) -> ApiPermissions:
        '''Replay does not query venue API-key permissions.'''

        msg = 'ReplayVenueAdapter does not support query_api_permissions'
        raise NotImplementedError(msg)

    def quantize_for_command(
        self,
        symbol: str,
        qty: Decimal,
        order_type: OrderType,
        *,
        reference_price: Decimal | None = None,
    ) -> CommandQuantization:
        '''Floor-snap a qty to the lot grid and gate against filters.'''

        filters = self._filters.get(symbol)
        if filters is None:
            return CommandQuantization(snapped_qty=qty, rejection_reason=None)

        if qty < filters.lot_min:
            return CommandQuantization(
                snapped_qty=None, rejection_reason=_REJECT_BELOW_MIN_QTY,
            )

        snapped = (qty // filters.lot_step) * filters.lot_step
        if snapped <= _ZERO or snapped < filters.lot_min:
            return CommandQuantization(
                snapped_qty=None, rejection_reason=_REJECT_BELOW_MIN_QTY,
            )

        if reference_price is not None and snapped * reference_price < filters.min_notional:
            return CommandQuantization(
                snapped_qty=None, rejection_reason=_REJECT_BELOW_MIN_NOTIONAL,
            )

        return CommandQuantization(snapped_qty=snapped, rejection_reason=None)

    async def submit_order(
        self,
        account_id: str,
        symbol: str,
        side: OrderSide,
        order_type: OrderType,
        qty: Decimal | None,
        *,
        price: Decimal | None = None,
        stop_price: Decimal | None = None,
        stop_limit_price: Decimal | None = None,
        client_order_id: str | None = None,
        time_in_force: str | None = None,
        quote_qty: Decimal | None = None,
    ) -> SubmitResult:
        '''Fill a market order fully at the current bar price.'''

        if order_type is not OrderType.MARKET:
            raise OrderRejectedError(
                f'replay venue supports MARKET only, got {order_type.value}',
                venue_code=_FILTER_REJECT_CODE,
                reason='unsupported_order_type',
            )

        fill_price = self._current_price
        if fill_price is None:
            raise OrderRejectedError(
                'replay venue has no current price',
                venue_code=_FILTER_REJECT_CODE,
                reason='no_price',
            )

        balances = self._accounts.get(account_id)
        if balances is None:
            raise OrderRejectedError(
                f'account not registered: {account_id}',
                venue_code=_FILTER_REJECT_CODE,
                reason='unknown_account',
            )

        if qty is not None and quote_qty is not None:
            raise OrderRejectedError(
                'qty and quote_qty are mutually exclusive',
                venue_code=_FILTER_REJECT_CODE,
                reason='qty_and_quote_qty',
            )

        if quote_qty is not None and side is not OrderSide.BUY:
            raise OrderRejectedError(
                'quote_qty is only valid for a MARKET BUY',
                venue_code=_FILTER_REJECT_CODE,
                reason='quote_qty_sell',
            )

        base_qty = self._resolve_base_qty(symbol, qty, quote_qty, fill_price)
        notional = base_qty * fill_price
        fee = notional * self._fee_rate
        base_asset = self._base_asset(symbol)

        self._settle(balances, side, base_asset, base_qty, notional, fee)

        self._seq += 1
        venue_order_id = f'rv-o-{self._seq}'
        venue_trade_id = f'rv-t-{self._seq}'
        resolved_coid = client_order_id or venue_order_id
        ts = self._clock()

        self._orders[resolved_coid] = VenueOrder(
            venue_order_id=venue_order_id,
            client_order_id=resolved_coid,
            status=OrderStatus.FILLED,
            symbol=symbol,
            side=side,
            order_type=order_type,
            qty=base_qty,
            filled_qty=base_qty,
            price=None,
        )
        self._trades.setdefault(account_id, []).append(
            VenueTrade(
                venue_trade_id=venue_trade_id,
                venue_order_id=venue_order_id,
                client_order_id=resolved_coid,
                symbol=symbol,
                side=side,
                qty=base_qty,
                price=fill_price,
                fee=fee,
                fee_asset=_QUOTE_ASSET,
                is_maker=False,
                timestamp=ts,
            )
        )

        fill = ImmediateFill(
            venue_trade_id=venue_trade_id,
            qty=base_qty,
            price=fill_price,
            fee=fee,
            fee_asset=_QUOTE_ASSET,
            is_maker=False,
        )

        return SubmitResult(
            venue_order_id=venue_order_id,
            status=OrderStatus.FILLED,
            immediate_fills=(fill,),
        )

    async def cancel_order(
        self,
        account_id: str,
        symbol: str,
        *,
        venue_order_id: str | None = None,
        client_order_id: str | None = None,
    ) -> CancelResult:
        '''Reject every cancel; replay orders fill immediately, none rest.'''

        raise NotFoundError('replay venue has no open orders to cancel')

    async def cancel_order_list(
        self,
        account_id: str,
        symbol: str,
        *,
        venue_order_id: str | None = None,
        client_order_id: str | None = None,
    ) -> CancelResult:
        '''Reject every list cancel; replay holds no resting order lists.'''

        raise NotFoundError('replay venue has no open order lists to cancel')

    async def query_order(
        self,
        account_id: str,
        symbol: str,
        *,
        venue_order_id: str | None = None,
        client_order_id: str | None = None,
    ) -> VenueOrder:
        '''Return a recorded (filled) order, or raise if unknown.'''

        if client_order_id is not None and client_order_id in self._orders:
            return self._orders[client_order_id]

        if venue_order_id is not None:
            for order in self._orders.values():
                if order.venue_order_id == venue_order_id:
                    return order

        raise NotFoundError(
            f'unknown order: venue_order_id={venue_order_id} '
            f'client_order_id={client_order_id}'
        )

    async def query_open_orders(
        self,
        account_id: str,
        symbol: str,
    ) -> list[VenueOrder]:
        '''Return no open orders; replay fills are immediate.'''

        return []

    async def query_balance(
        self,
        account_id: str,
        assets: frozenset[str],
    ) -> list[BalanceEntry]:
        '''Return free balances for the requested assets.'''

        balances = self._accounts.get(account_id, {})

        return [
            BalanceEntry(asset=asset, free=balances.get(asset, _ZERO), locked=_ZERO)
            for asset in assets
        ]

    async def query_trades(
        self,
        account_id: str,
        symbol: str,
        *,
        from_id: int | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        limit: int | None = None,
    ) -> list[VenueTrade]:
        '''Return recorded fills for a symbol, filtered by cursor, time window, and limit.'''

        if from_id is not None and (start_time is not None or end_time is not None):
            msg = 'from_id cannot be combined with start_time or end_time'
            raise ValueError(msg)

        trades = [
            trade
            for trade in self._trades.get(account_id, [])
            if trade.symbol == symbol
        ]

        if from_id is not None:
            trades = [
                trade for trade in trades
                if _replay_trade_seq(trade.venue_trade_id) >= from_id
            ]

        if start_time is not None:
            trades = [trade for trade in trades if trade.timestamp >= start_time]

        if end_time is not None:
            trades = [trade for trade in trades if trade.timestamp <= end_time]

        if limit is not None:
            trades = trades[:limit]

        return trades

    async def get_exchange_info(self, symbol: str) -> SymbolFilters:
        '''Return cached filters for a symbol, or raise if unknown.'''

        filters = self._filters.get(symbol)
        if filters is None:
            raise NotFoundError(f'no filters for symbol: {symbol}')

        return filters

    async def query_order_book(
        self,
        symbol: str,
        *,
        limit: int = 20,
    ) -> OrderBookSnapshot:
        '''Return a one-level book at the current price for slippage estimates.'''

        if self._current_price is None:
            raise NotFoundError('replay venue has no current price')

        level = OrderBookLevel(price=self._current_price, qty=_ZERO)

        return OrderBookSnapshot(bids=(level,), asks=(level,), last_update_id=self._seq)

    async def get_server_time(self) -> int:
        '''Return the current simulated time in epoch milliseconds.'''

        return int(self._clock().timestamp() * _MS_PER_SECOND)

    def get_health_snapshot(self, account_id: str) -> HealthSnapshot:
        '''Return default (healthy) metrics; replay has no real latency.'''

        return HealthSnapshot()

    async def load_filters(self, symbols: Sequence[str]) -> None:
        '''No-op; filters are provided at construction.'''

    def cached_filters(self, symbol: str) -> SymbolFilters | None:
        '''Return cached filters for a symbol, or None if not loaded.'''

        return self._filters.get(symbol)

    def parse_execution_report(self, data: dict[str, Any]) -> ExecutionReport:
        '''Unsupported; replay delivers fills synchronously, not via a stream.'''

        msg = 'replay venue has no execution-report stream'
        raise NotImplementedError(msg)

    async def close(self) -> None:
        '''No persistent resources to release.'''

    def _resolve_base_qty(
        self,
        symbol: str,
        qty: Decimal | None,
        quote_qty: Decimal | None,
        fill_price: Decimal,
    ) -> Decimal:
        '''Derive the base quantity from `qty` or quote-native `quote_qty`.'''

        if quote_qty is not None:
            base_qty = quote_qty / fill_price
            filters = self._filters.get(symbol)
            if filters is not None:
                base_qty = (base_qty // filters.lot_step) * filters.lot_step
        elif qty is not None:
            base_qty = qty
        else:
            raise OrderRejectedError(
                'one of qty or quote_qty is required',
                venue_code=_FILTER_REJECT_CODE,
                reason='missing_qty',
            )

        if base_qty <= _ZERO:
            raise OrderRejectedError(
                f'order quantity resolves to non-positive: {base_qty}',
                venue_code=_FILTER_REJECT_CODE,
                reason='non_positive_qty',
            )

        return base_qty

    def _settle(
        self,
        balances: dict[str, Decimal],
        side: OrderSide,
        base_asset: str,
        qty: Decimal,
        notional: Decimal,
        fee: Decimal,
    ) -> None:
        '''Debit and credit the account's balances for a filled order.'''

        if side is OrderSide.BUY:
            cost = notional + fee
            if balances.get(_QUOTE_ASSET, _ZERO) < cost:
                raise OrderRejectedError(
                    f'insufficient {_QUOTE_ASSET} balance',
                    venue_code=_FILTER_REJECT_CODE,
                    reason='insufficient_balance',
                )
            balances[_QUOTE_ASSET] = balances.get(_QUOTE_ASSET, _ZERO) - cost
            balances[base_asset] = balances.get(base_asset, _ZERO) + qty
        else:
            if balances.get(base_asset, _ZERO) < qty:
                raise OrderRejectedError(
                    f'insufficient {base_asset} balance',
                    venue_code=_FILTER_REJECT_CODE,
                    reason='insufficient_balance',
                )
            balances[base_asset] = balances.get(base_asset, _ZERO) - qty
            balances[_QUOTE_ASSET] = balances.get(_QUOTE_ASSET, _ZERO) + (notional - fee)

    @staticmethod
    def _base_asset(symbol: str) -> str:
        '''Return the base asset of a quote-denominated symbol.'''

        if not symbol.endswith(_QUOTE_ASSET):
            msg = f'symbol must be quoted in {_QUOTE_ASSET}, got {symbol}'
            raise ValueError(msg)

        return symbol[: -len(_QUOTE_ASSET)]
