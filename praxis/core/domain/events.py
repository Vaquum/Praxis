'''
Event type dataclasses for the Praxis Trading sub-system.

Represent domain events consumed by TradingState.apply(). Each event
is an immutable fact produced by the execution pipeline and projected
onto in-memory state. Only event types needed for position and order
tracking are defined here; later WPs add remaining types.
'''

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from praxis.core.domain._require_str import _require_str
from praxis.core.domain.enums import OrderSide, OrderType, TradeStatus

__all__ = [
    'CommandAccepted',
    'Event',
    'FillReceived',
    'OrderAcked',
    'OrderCanceled',
    'OrderExpired',
    'OrderRejected',
    'OrderSubmitFailed',
    'OrderSubmitIntent',
    'OrderSubmitted',
    'OutcomeAcked',
    'OutcomeDeliveryContextRecorded',
    'OutcomeReplayAbandoned',
    'TradeClosed',
    'TradeOutcomeProduced',
]

_ZERO = Decimal(0)


@dataclass(frozen=True)
class _EventBase:

    '''
    Represent shared fields for all domain events.

    Args:
        account_id (str): Account that owns this event.
        timestamp (datetime): Event time, must be timezone-aware.
    '''

    account_id: str
    timestamp: datetime

    def __post_init__(self) -> None:

        name = type(self).__name__
        _require_str(name, 'account_id', self.account_id)

        if self.timestamp.tzinfo is None or self.timestamp.utcoffset() is None:
            msg = f'{name}.timestamp must be timezone-aware'
            raise ValueError(msg)


@dataclass(frozen=True)
class CommandAccepted(_EventBase):

    '''
    Represent acceptance of a TradeCommand into the execution pipeline.

    Args:
        account_id (str): Account that owns this event.
        timestamp (datetime): Event time, must be timezone-aware.
        command_id (str): Originating TradeCommand identifier.
        trade_id (str): Trade correlation identifier.
        strategy_id (str | None): Nexus strategy identifier for position attribution.
    '''

    command_id: str
    trade_id: str
    strategy_id: str | None = None

    def __post_init__(self) -> None:

        super().__post_init__()

        name = type(self).__name__
        _require_str(name, 'command_id', self.command_id)
        _require_str(name, 'trade_id', self.trade_id)


@dataclass(frozen=True)
class OrderSubmitIntent(_EventBase):

    '''
    Represent intent to submit an order before venue acknowledgement.

    Args:
        account_id (str): Account that owns this event.
        timestamp (datetime): Event time, must be timezone-aware.
        command_id (str): Originating TradeCommand identifier.
        trade_id (str): Trade correlation identifier.
        client_order_id (str): Deterministic client order identifier.
        symbol (str): Trading pair symbol.
        side (OrderSide): Order direction.
        order_type (OrderType): Order type.
        qty (Decimal | None): Base-asset quantity. Mutually exclusive
            with `quote_qty` — exactly one must be set.
        quote_qty (Decimal | None): Quote-asset spend (e.g. USDT) for
            quote-native MARKET BUY. Mutually exclusive with `qty`.
        price (Decimal | None): Limit price, must be positive when set.
        stop_price (Decimal | None): Stop trigger price, must be positive when set.
        stop_limit_price (Decimal | None): Stop-limit price for OCO orders, must be positive when set.
    '''

    command_id: str
    trade_id: str
    client_order_id: str
    symbol: str
    side: OrderSide
    order_type: OrderType
    qty: Decimal | None = None
    price: Decimal | None = None
    stop_price: Decimal | None = None
    stop_limit_price: Decimal | None = None
    quote_qty: Decimal | None = None

    def __post_init__(self) -> None:

        super().__post_init__()

        name = type(self).__name__
        _require_str(name, 'command_id', self.command_id)
        _require_str(name, 'trade_id', self.trade_id)
        _require_str(name, 'client_order_id', self.client_order_id)
        _require_str(name, 'symbol', self.symbol)

        if (self.qty is None) == (self.quote_qty is None):
            msg = 'OrderSubmitIntent requires exactly one of qty or quote_qty'
            raise ValueError(msg)

        if self.qty is not None and (
            not isinstance(self.qty, Decimal)
            or not self.qty.is_finite()
            or self.qty <= _ZERO
        ):
            msg = 'OrderSubmitIntent.qty must be a finite positive Decimal'
            raise ValueError(msg)

        if self.quote_qty is not None and (
            not isinstance(self.quote_qty, Decimal)
            or not self.quote_qty.is_finite()
            or self.quote_qty <= _ZERO
        ):
            msg = 'OrderSubmitIntent.quote_qty must be a finite positive Decimal'
            raise ValueError(msg)

        if self.price is not None and self.price <= _ZERO:
            msg = 'OrderSubmitIntent.price must be positive'
            raise ValueError(msg)

        if self.stop_price is not None and self.stop_price <= _ZERO:
            msg = 'OrderSubmitIntent.stop_price must be positive'
            raise ValueError(msg)

        if self.stop_limit_price is not None and self.stop_limit_price <= _ZERO:
            msg = 'OrderSubmitIntent.stop_limit_price must be positive'
            raise ValueError(msg)


@dataclass(frozen=True)
class OrderSubmitted(_EventBase):

    '''
    Represent successful order submission to the venue.

    Args:
        account_id (str): Account that owns this event.
        timestamp (datetime): Event time, must be timezone-aware.
        client_order_id (str): Deterministic client order identifier.
        venue_order_id (str): Venue-assigned order identifier.
    '''

    client_order_id: str
    venue_order_id: str

    def __post_init__(self) -> None:

        super().__post_init__()

        name = type(self).__name__
        _require_str(name, 'client_order_id', self.client_order_id)
        _require_str(name, 'venue_order_id', self.venue_order_id)


@dataclass(frozen=True)
class OrderQuoteNativeFilled(_EventBase):

    '''
    Mark a quote-native order as terminally FILLED.

    Qty-native orders self-terminate when `Order.filled_qty` reaches
    `Order.qty`, which is implicit in the `FillReceived` projection.
    Quote-native MARKET BUYs have no base target, so the venue's
    per-response `status == FILLED` flag is the only terminal signal
    — this event persists that transition so spine replay reconstructs
    the order as closed instead of stranded `PARTIALLY_FILLED`.

    Args:
        account_id (str): Account that owns this event.
        timestamp (datetime): Event time, must be timezone-aware.
        client_order_id (str): Deterministic client order identifier.
    '''

    client_order_id: str

    def __post_init__(self) -> None:

        super().__post_init__()

        name = type(self).__name__
        _require_str(name, 'client_order_id', self.client_order_id)


@dataclass(frozen=True)
class OrderSubmitFailed(_EventBase):

    '''
    Represent a failed order submission attempt.

    Args:
        account_id (str): Account that owns this event.
        timestamp (datetime): Event time, must be timezone-aware.
        client_order_id (str): Deterministic client order identifier.
        reason (str): Failure reason from venue or internal logic.
    '''

    client_order_id: str
    reason: str

    def __post_init__(self) -> None:

        super().__post_init__()

        name = type(self).__name__
        _require_str(name, 'client_order_id', self.client_order_id)
        _require_str(name, 'reason', self.reason)


@dataclass(frozen=True)
class OrderAcked(_EventBase):

    '''
    Represent venue acknowledgement of an order.

    Args:
        account_id (str): Account that owns this event.
        timestamp (datetime): Event time, must be timezone-aware.
        client_order_id (str): Deterministic client order identifier.
        venue_order_id (str): Venue-assigned order identifier.
    '''

    client_order_id: str
    venue_order_id: str

    def __post_init__(self) -> None:

        super().__post_init__()

        name = type(self).__name__
        _require_str(name, 'client_order_id', self.client_order_id)
        _require_str(name, 'venue_order_id', self.venue_order_id)


@dataclass(frozen=True)
class FillReceived(_EventBase):

    '''
    Represent a fill execution reported by the venue.

    Args:
        account_id (str): Account that owns this event.
        timestamp (datetime): Event time, must be timezone-aware.
        client_order_id (str): Deterministic client order identifier.
        venue_order_id (str): Venue-assigned order identifier.
        venue_trade_id (str): Venue-assigned unique trade identifier.
        trade_id (str): Trade correlation identifier.
        command_id (str): Originating TradeCommand identifier.
        symbol (str): Trading pair symbol.
        side (OrderSide): Fill direction.
        qty (Decimal): Filled quantity, must be positive.
        price (Decimal): Execution price, must be positive.
        fee (Decimal): Transaction fee, must be non-negative.
        fee_asset (str): Asset in which the fee is denominated.
        is_maker (bool): Whether the fill was a maker trade.
    '''

    client_order_id: str
    venue_order_id: str
    venue_trade_id: str
    trade_id: str
    command_id: str
    symbol: str
    side: OrderSide
    qty: Decimal
    price: Decimal
    fee: Decimal
    fee_asset: str
    is_maker: bool

    def __post_init__(self) -> None:

        super().__post_init__()

        name = type(self).__name__
        _require_str(name, 'client_order_id', self.client_order_id)
        _require_str(name, 'venue_order_id', self.venue_order_id)
        _require_str(name, 'venue_trade_id', self.venue_trade_id)
        _require_str(name, 'trade_id', self.trade_id)
        _require_str(name, 'command_id', self.command_id)
        _require_str(name, 'symbol', self.symbol)
        _require_str(name, 'fee_asset', self.fee_asset)

        if self.qty <= _ZERO:
            msg = 'FillReceived.qty must be positive'
            raise ValueError(msg)

        if self.price <= _ZERO:
            msg = 'FillReceived.price must be positive'
            raise ValueError(msg)

        if self.fee < _ZERO:
            msg = 'FillReceived.fee must be non-negative'
            raise ValueError(msg)


@dataclass(frozen=True)
class OrderRejected(_EventBase):

    '''
    Represent a venue rejection of an order.

    Args:
        account_id (str): Account that owns this event.
        timestamp (datetime): Event time, must be timezone-aware.
        client_order_id (str): Deterministic client order identifier.
        venue_order_id (str | None): Venue-assigned order identifier, if available.
        reason (str): Rejection reason from venue.
    '''

    client_order_id: str
    venue_order_id: str | None
    reason: str

    def __post_init__(self) -> None:

        super().__post_init__()

        name = type(self).__name__
        _require_str(name, 'client_order_id', self.client_order_id)
        _require_str(name, 'venue_order_id', self.venue_order_id, optional=True)
        _require_str(name, 'reason', self.reason)


@dataclass(frozen=True)
class OrderCanceled(_EventBase):

    '''
    Represent cancellation of an order.

    Args:
        account_id (str): Account that owns this event.
        timestamp (datetime): Event time, must be timezone-aware.
        client_order_id (str): Deterministic client order identifier.
        venue_order_id (str | None): Venue-assigned order identifier, if available.
        reason (str | None): Cancellation reason, if available.
    '''

    client_order_id: str
    venue_order_id: str | None
    reason: str | None

    def __post_init__(self) -> None:

        super().__post_init__()

        name = type(self).__name__
        _require_str(name, 'client_order_id', self.client_order_id)
        _require_str(name, 'venue_order_id', self.venue_order_id, optional=True)
        _require_str(name, 'reason', self.reason, optional=True)


@dataclass(frozen=True)
class OrderExpired(_EventBase):

    '''
    Represent expiration of an order.

    Args:
        account_id (str): Account that owns this event.
        timestamp (datetime): Event time, must be timezone-aware.
        client_order_id (str): Deterministic client order identifier.
        venue_order_id (str | None): Venue-assigned order identifier, if available.
    '''

    client_order_id: str
    venue_order_id: str | None

    def __post_init__(self) -> None:

        super().__post_init__()

        name = type(self).__name__
        _require_str(name, 'client_order_id', self.client_order_id)
        _require_str(name, 'venue_order_id', self.venue_order_id, optional=True)


@dataclass(frozen=True)
class TradeClosed(_EventBase):

    '''
    Represent closure of a trade lifecycle.

    Args:
        account_id (str): Account that owns this event.
        timestamp (datetime): Event time, must be timezone-aware.
        trade_id (str): Trade correlation identifier.
        command_id (str): Originating TradeCommand identifier.
    '''

    trade_id: str
    command_id: str

    def __post_init__(self) -> None:

        super().__post_init__()

        name = type(self).__name__
        _require_str(name, 'trade_id', self.trade_id)
        _require_str(name, 'command_id', self.command_id)


@dataclass(frozen=True)
class TradeOutcomeProduced(_EventBase):

    '''
    Represent production of a TradeOutcome for audit and replay.

    Args:
        account_id (str): Account that owns this event.
        timestamp (datetime): Event time, must be timezone-aware.
        command_id (str): Originating TradeCommand identifier.
        trade_id (str): Trade correlation identifier.
        status (TradeStatus): Outcome status at time of production.
        reason (str | None): Descriptive reason for status.
        filled_qty (Decimal): Cumulative filled quantity carried from the
            `TradeOutcome`, so boot replay (TD-052) can rebuild the Praxis
            outcome and re-run `OutcomeTranslator` to derive the same
            deterministic Nexus `outcome_id`s. Defaults to `_ZERO` for
            no-fill outcomes and for pre-TD-052 events on replay.
        cumulative_notional (Decimal): Venue-side cumulative notional
            (sum of fill qty * price) carried from the `TradeOutcome`,
            the other input the translator needs to derive fill deltas.
        target_qty (Decimal | None): Command target quantity, used by the
            translator to derive `remaining_size`. None when unknown.
    '''

    command_id: str
    trade_id: str
    status: TradeStatus
    reason: str | None = None
    filled_qty: Decimal = _ZERO
    cumulative_notional: Decimal = _ZERO
    target_qty: Decimal | None = None

    def __post_init__(self) -> None:

        super().__post_init__()

        name = type(self).__name__
        _require_str(name, 'command_id', self.command_id)
        _require_str(name, 'trade_id', self.trade_id)
        _require_str(name, 'reason', self.reason, optional=True)

        if self.filled_qty < _ZERO:
            msg = 'TradeOutcomeProduced.filled_qty must be non-negative'
            raise ValueError(msg)

        if self.cumulative_notional < _ZERO:
            msg = 'TradeOutcomeProduced.cumulative_notional must be non-negative'
            raise ValueError(msg)

        if self.target_qty is not None and self.target_qty <= _ZERO:
            msg = 'TradeOutcomeProduced.target_qty must be positive when set'
            raise ValueError(msg)


@dataclass(frozen=True)
class OutcomeAcked(_EventBase):

    '''
    Represent successful application of a TradeOutcome at the consumer.

    Round-18 MAJOR-004: appended by the launcher's process_outcome
    closure after `OutcomeProcessor.process` returns success and the
    follow-on `state_store.append_mutation` lands. The recorded
    `outcome_id` is the Nexus-side `outcome_id`, not a Praxis-level
    identifier, and one Praxis `TradeOutcome` fans out via
    `OutcomeTranslator` to multiple Nexus outcomes (ACK + zero-or-more
    PARTIAL + a terminal), each producing its own `OutcomeAcked`. Boot
    replay (TD-052, deferred) computes the full set of derived Nexus
    outcome_ids for each `TradeOutcomeProduced` and re-delivers any
    `TradeOutcomeProduced` with at least one derived id missing a
    matching `OutcomeAcked`. Missing `OutcomeAcked` is not by itself
    sufficient evidence that Nexus did not mutate, because Nexus may
    have applied the outcome and persisted a checkpoint before the ack
    landed; the replay implementation must additionally consult the
    Nexus-side durable applied-outcome marker provided by TD-086, which
    is a paired-boundary requirement (TD-052 must not ship without
    TD-086).

    Args:
        account_id (str): Account that owns this event.
        timestamp (datetime): Event time, must be timezone-aware.
        outcome_id (str): Nexus-side outcome identifier
            (`NexusTradeOutcome.outcome_id`) emitted by `OutcomeTranslator`
            and acked by the launcher after `OutcomeProcessor.process`
            returns success. Praxis `TradeOutcome` does not carry an
            `outcome_id` field today; that field is part of the TD-052
            prework (migration step 1).
    '''

    outcome_id: str

    def __post_init__(self) -> None:

        super().__post_init__()

        name = type(self).__name__
        _require_str(name, 'outcome_id', self.outcome_id)


@dataclass(frozen=True)
class OutcomeReplayAbandoned(_EventBase):

    '''Mark a boot-replayed Nexus outcome that could not be applied.

    Boot replay (TD-052) re-delivers an unacked `outcome_id`. Some
    legs can never be applied on a retry — e.g. a never-applied entry
    fill whose `CapitalController` order was cleared by `reconcile_at_boot`,
    so `order_fill` returns `order not found`. Without a durable marker
    such a leg would be re-planned and re-fail on every subsequent boot.
    This event records that replay has given up on the `outcome_id`; the
    boot-replay planner subtracts these ids so the leg is not retried.
    The underlying venue/Nexus divergence is owned by the boot capital
    reconcile, not by replay. Carries no execution truth and
    `TradingState.apply` ignores it.

    Args:
        account_id (str): Account that owns this event.
        timestamp (datetime): Event time, must be timezone-aware.
        outcome_id (str): Nexus-side outcome identifier replay abandoned.
        reason (str): Why the leg could not be applied (operator context).
    '''

    outcome_id: str
    reason: str

    def __post_init__(self) -> None:

        super().__post_init__()

        name = type(self).__name__
        _require_str(name, 'outcome_id', self.outcome_id)
        _require_str(name, 'reason', self.reason)


@dataclass(frozen=True)
class OutcomeDeliveryContextRecorded(_EventBase):

    '''Persist the Nexus delivery `OrderContext` for a submitted command.

    The launcher builds an `OrderContext` (Nexus connector routing
    metadata: `strategy_id`, `is_entry`, `order_notional`,
    `estimated_fees`, `order_size`, `intended_full_close`) from the
    strategy `Action` at submit time and holds it only in the in-memory
    `command_contexts` map, which is empty after a restart. Boot replay
    (TD-052) needs that context to re-route an unacked `TradeOutcomeProduced`
    through `OutcomeProcessor.process`. This event durably records the
    context on the spine at submit time, keyed by `command_id`, so the
    boot-replay step can rebuild the `OrderContext` without the live map.
    It carries no execution truth and `TradingState.apply` ignores it.

    Args:
        account_id (str): Account that owns this event.
        timestamp (datetime): Event time, must be timezone-aware.
        command_id (str): Command the context belongs to.
        side (OrderSide): Venue order direction.
        is_entry (bool): True when the order grows a position (ENTER).
        order_notional (Decimal): Order notional in quote asset.
        estimated_fees (Decimal): Estimated fees at reservation time.
        strategy_id (str | None): Owning strategy, None when unattributed.
        trade_id (str | None): Position reference; None for a new entry
            until assigned.
        order_size (Decimal | None): Order size in base asset; None for a
            quote-native ENTER.
        intended_full_close (bool): True on an EXIT meant to close the
            trade completely (drives dust-close routing downstream).
    '''

    command_id: str
    side: OrderSide
    is_entry: bool
    order_notional: Decimal
    estimated_fees: Decimal
    strategy_id: str | None = None
    trade_id: str | None = None
    order_size: Decimal | None = None
    intended_full_close: bool = False

    def __post_init__(self) -> None:

        super().__post_init__()

        name = type(self).__name__
        _require_str(name, 'command_id', self.command_id)
        _require_str(name, 'strategy_id', self.strategy_id, optional=True)
        _require_str(name, 'trade_id', self.trade_id, optional=True)

        if not isinstance(self.side, OrderSide):
            msg = f'{name}.side must be an OrderSide'
            raise ValueError(msg)

        if not isinstance(self.is_entry, bool):
            msg = f'{name}.is_entry must be a bool'
            raise ValueError(msg)

        if not isinstance(self.intended_full_close, bool):
            msg = f'{name}.intended_full_close must be a bool'
            raise ValueError(msg)

        if self.order_notional < _ZERO:
            msg = f'{name}.order_notional must be non-negative'
            raise ValueError(msg)

        if self.estimated_fees < _ZERO:
            msg = f'{name}.estimated_fees must be non-negative'
            raise ValueError(msg)

        if self.order_size is not None and self.order_size <= _ZERO:
            msg = f'{name}.order_size must be positive when set'
            raise ValueError(msg)


type Event = (
    CommandAccepted
    | OrderSubmitIntent
    | OrderSubmitted
    | OrderSubmitFailed
    | OrderQuoteNativeFilled
    | OrderAcked
    | FillReceived
    | OrderRejected
    | OrderCanceled
    | OrderExpired
    | TradeClosed
    | TradeOutcomeProduced
    | OutcomeAcked
    | OutcomeDeliveryContextRecorded
    | OutcomeReplayAbandoned
)
