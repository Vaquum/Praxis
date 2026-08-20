'''
Event type dataclasses for the Praxis Trading sub-system.

Represent domain events consumed by TradingState.apply(). Each event
is an immutable fact produced by the execution pipeline and projected
onto in-memory state or consumed by other projections. Covers position
and order tracking, scheme and bracket lifecycle, reconciliation, and
the bracket protective-OCO amend state machine.
'''

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from praxis.core.domain._require_str import _require_str
from praxis.core.domain.enums import (
    CostBasisMethod,
    ExecutionMode,
    FundDirection,
    OrderSide,
    OrderType,
    SchemeState,
    TradeStatus,
)

__all__ = [
    'BracketInitialized',
    'CommandAccepted',
    'Event',
    'FillReceived',
    'FlattenInitiated',
    'FundTransaction',
    'MarkSampled',
    'OperatorHaltRequested',
    'OperatorResumeRequested',
    'OrderAcked',
    'OrderAmendInitiated',
    'OrderCanceled',
    'OrderExpired',
    'OrderRejected',
    'OrderSubmitFailed',
    'OrderSubmitIntent',
    'OrderSubmitted',
    'OutcomeAcked',
    'OutcomeDeliveryContextRecorded',
    'OutcomeReplayAbandoned',
    'ProtectionActive',
    'ProtectionAmendRequested',
    'ProtectionCancelConfirmed',
    'ProtectionFailed',
    'ProtectionRemediationDelivered',
    'ProtectionReplaceSubmitted',
    'ProtectionStateUnknown',
    'ReconciliationMismatch',
    'RegisterAccount',
    'SchemeFrozen',
    'SchemeInitialized',
    'SchemeStateChanged',
    'SliceFailed',
    'TradeClosed',
    'TradeOutcomeProduced',
]

_ZERO = Decimal(0)
_MIN_PROTECTION_VERSION = 1
_COST_BASIS_METHOD_VALUES = frozenset(method.value for method in CostBasisMethod)
_FUND_DIRECTION_VALUES = frozenset(direction.value for direction in FundDirection)


def _require_protection_version(cls: str, value: int) -> None:

    '''
    Validate that a protective-OCO revision is an int at or above the minimum.

    Args:
        cls (str): Class name for error context.
        value (int): Protective-OCO revision to validate.
    '''

    if isinstance(value, bool) or not isinstance(value, int) or value < _MIN_PROTECTION_VERSION:
        msg = f'{cls}.protection_version must be an int >= {_MIN_PROTECTION_VERSION}'
        raise ValueError(msg)


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
        leg_client_order_ids (tuple[str, ...]): For an OCO submission, the
            venue-assigned client order ids of the list's legs, persisted so
            replay can map leg fills back to the parent order. Empty for
            non-OCO orders.
    '''

    client_order_id: str
    venue_order_id: str
    leg_client_order_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:

        super().__post_init__()

        object.__setattr__(
            self, 'leg_client_order_ids', tuple(self.leg_client_order_ids),
        )

        name = type(self).__name__
        _require_str(name, 'client_order_id', self.client_order_id)
        _require_str(name, 'venue_order_id', self.venue_order_id)

        for leg_id in self.leg_client_order_ids:
            _require_str(name, 'leg_client_order_ids entry', leg_id)


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
class SliceFailed(_EventBase):

    '''
    Represent a scheme slice that could not be placed.

    Appended when a multi-slice scheme's child submission fails
    definitively (venue rejection, insufficient balance, rate limit after
    retries). The scheme reports a non-terminal PARTIAL outcome and waits
    for the Manager (TradeModify / TradeAbort) or its deadline.

    Args:
        account_id (str): Account that owns this event.
        timestamp (datetime): Event time, must be timezone-aware.
        command_id (str): Parent scheme identifier.
        client_order_id (str): Deterministic client order id of the failed slice.
        reason (str): Failure reason.
    '''

    command_id: str
    client_order_id: str
    reason: str

    def __post_init__(self) -> None:

        super().__post_init__()

        name = type(self).__name__
        _require_str(name, 'command_id', self.command_id)
        _require_str(name, 'client_order_id', self.client_order_id)
        _require_str(name, 'reason', self.reason)


@dataclass(frozen=True)
class SchemeFrozen(_EventBase):

    '''
    Represent a running scheme durably frozen against firing further slices.

    Appended when a naked-protection remediation freezes an account's live
    schemes: no further slices are scheduled, and on replay the scheme
    resumes frozen rather than re-arming its timer, so a restart cannot
    resurrect the buying. Distinct from SliceFailed, which reports a
    per-slice failure with a PARTIAL outcome; a freeze reports no outcome
    and names no slice.

    Args:
        account_id (str): Account that owns this event.
        timestamp (datetime): Event time, must be timezone-aware.
        command_id (str): Frozen scheme identifier.
        reason (str): Freeze reason.
    '''

    command_id: str
    reason: str

    def __post_init__(self) -> None:

        super().__post_init__()

        name = type(self).__name__
        _require_str(name, 'command_id', self.command_id)
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
class SchemeInitialized(_EventBase):

    '''
    Represent the start of a multi-slice execution scheme.

    Written once when a non-single-shot command begins execution. Records
    the immutable identity and totals needed to recognise and resume the
    scheme from the Event Spine after a restart. Mutable progress is
    recorded by SchemeStateChanged.

    Args:
        account_id (str): Account that owns this event.
        timestamp (datetime): Event time, must be timezone-aware.
        command_id (str): Originating TradeCommand identifier, the scheme parent id.
        trade_id (str): Trade correlation identifier.
        execution_mode (ExecutionMode): The scheme's execution mode.
        symbol (str): Trading pair symbol.
        side (OrderSide): Order direction.
        total_qty (Decimal): Total base quantity to execute across children.
        slices_total (int): Planned number of children, or 0 when dynamic.
        interval_seconds (int): Seconds between time-scheduled children, so
            boot replay can rebuild the schedule without the transient
            command. Non-negative; 0 for modes that are not time-scheduled.
            Defaults to 0 so historical events written before this field
            hydrate cleanly; boot resume treats a 0 interval as unresumable.
        timeout_seconds (int): Command deadline in seconds from the scheme's
            start, persisted so the deadline backstop survives a restart.
            Non-negative; 0 means no deadline. Defaults to 0 so events
            written before this field hydrate cleanly.
        volume_weights (tuple[Decimal, ...]): Per-child fractional weights
            (summing to 1) for a scheme whose children are unequally sized —
            a Scheduled VWAP volume curve or a Ladder DCA level allocation —
            persisted so boot resume can reconstruct the grid, which slice
            count and interval alone cannot. Empty for equal-slice modes.
            Defaults to empty so events written before this field hydrate
            cleanly.
        price_levels (tuple[Decimal, ...]): Per-level resting limit prices
            for a Ladder DCA scheme, persisted for a faithful rebuild on
            resume. Empty for modes with no per-child price. Defaults to
            empty so events written before this field hydrate cleanly.
    '''

    command_id: str
    trade_id: str
    execution_mode: ExecutionMode
    symbol: str
    side: OrderSide
    total_qty: Decimal
    slices_total: int
    interval_seconds: int = 0
    timeout_seconds: int = 0
    volume_weights: tuple[Decimal, ...] = ()
    price_levels: tuple[Decimal, ...] = ()

    def __post_init__(self) -> None:

        super().__post_init__()

        object.__setattr__(self, 'volume_weights', tuple(self.volume_weights))
        object.__setattr__(self, 'price_levels', tuple(self.price_levels))

        name = type(self).__name__
        _require_str(name, 'command_id', self.command_id)
        _require_str(name, 'trade_id', self.trade_id)
        _require_str(name, 'symbol', self.symbol)

        if self.execution_mode is ExecutionMode.SINGLE_SHOT:
            msg = f'{name}.execution_mode must not be SINGLE_SHOT'
            raise ValueError(msg)

        if (
            not isinstance(self.total_qty, Decimal)
            or not self.total_qty.is_finite()
            or self.total_qty <= _ZERO
        ):
            msg = f'{name}.total_qty must be a positive, finite Decimal'
            raise ValueError(msg)

        if self.slices_total < 0:
            msg = f'{name}.slices_total must be non-negative'
            raise ValueError(msg)

        if self.interval_seconds < 0:
            msg = f'{name}.interval_seconds must be non-negative'
            raise ValueError(msg)

        if self.timeout_seconds < 0:
            msg = f'{name}.timeout_seconds must be non-negative'
            raise ValueError(msg)

        for weight in self.volume_weights:
            if not isinstance(weight, Decimal) or not weight.is_finite() or weight <= _ZERO:
                msg = f'{name}.volume_weights entries must be positive, finite Decimals'
                raise ValueError(msg)

        for level in self.price_levels:
            if not isinstance(level, Decimal) or not level.is_finite() or level <= _ZERO:
                msg = f'{name}.price_levels entries must be positive, finite Decimals'
                raise ValueError(msg)


@dataclass(frozen=True)
class BracketInitialized(_EventBase):

    '''
    Represent the start of a bracket execution.

    Written once when a bracket command begins, before the entry submit, so
    the identity and protective parameters survive a restart: boot resume
    reconstructs the bracket to place the protective OCO for a filled-but-
    unprotected entry, or to re-track an entry still awaiting its fill.

    Args:
        account_id (str): Account that owns this event.
        timestamp (datetime): Event time, must be timezone-aware.
        command_id (str): Originating bracket command identifier.
        trade_id (str): Trade correlation identifier.
        symbol (str): Trading pair symbol.
        side (OrderSide): Entry order direction.
        total_qty (Decimal): Entry base quantity.
        take_profit_price (Decimal | None): Absolute take-profit price.
        take_profit_offset_bps (Decimal | None): Take-profit offset in basis
            points from the entry average fill.
        stop_loss_price (Decimal | None): Absolute stop-loss trigger price.
        stop_loss_offset_bps (Decimal | None): Stop-loss offset in basis
            points from the entry average fill.
        stop_loss_limit_price (Decimal | None): Stop-loss limit price, or None
            for a stop-market stop-loss leg.
        timeout_seconds (int): Command deadline in seconds. Non-negative;
            0 means no deadline. Defaults to 0.
    '''

    command_id: str
    trade_id: str
    symbol: str
    side: OrderSide
    total_qty: Decimal
    take_profit_price: Decimal | None = None
    take_profit_offset_bps: Decimal | None = None
    stop_loss_price: Decimal | None = None
    stop_loss_offset_bps: Decimal | None = None
    stop_loss_limit_price: Decimal | None = None
    timeout_seconds: int = 0

    def __post_init__(self) -> None:

        super().__post_init__()

        name = type(self).__name__
        _require_str(name, 'command_id', self.command_id)
        _require_str(name, 'trade_id', self.trade_id)
        _require_str(name, 'symbol', self.symbol)

        if (
            not isinstance(self.total_qty, Decimal)
            or not self.total_qty.is_finite()
            or self.total_qty <= _ZERO
        ):
            msg = f'{name}.total_qty must be a positive, finite Decimal'
            raise ValueError(msg)

        if self.timeout_seconds < 0:
            msg = f'{name}.timeout_seconds must be non-negative'
            raise ValueError(msg)


@dataclass(frozen=True)
class ProtectionAmendRequested(_EventBase):

    '''
    Represent the intent to amend a bracket's protective OCO, before the
    venue cancel.

    Persisted first in the protective-OCO amend sequence and carries the
    complete, resolved replacement OCO — both legs as absolute prices, not a
    partial patch — so recovery is self-contained: if the process dies
    between this durable write and the venue cancel/replace, boot re-places
    exactly these legs without re-deriving offsets from the entry fill. A
    partial amend (e.g. take-profit only) is merged against the bracket's
    current protection into a full two-leg snapshot before this event is
    written.

    Args:
        account_id (str): Account that owns this event.
        timestamp (datetime): Event time, must be timezone-aware.
        command_id (str): Bracket command whose protective OCO is amended.
        protection_version (int): Amend attempt identifier, starting at 1 and
            incremented on every `ProtectionAmendRequested` — including a
            retry after a `ProtectionFailed` — so each attempt (and its
            `new_list_client_order_id`) is uniquely addressable on replay. It
            is not a count of successful amends.
        new_list_client_order_id (str): Client list order id of the
            replacement OCO to place. Must differ from
            `old_list_client_order_id`.
        old_list_client_order_id (str): Client list order id of the resting
            OCO to cancel.
        take_profit_price (Decimal): Resolved absolute take-profit price of
            the replacement OCO.
        stop_loss_price (Decimal): Resolved absolute stop-loss trigger price
            of the replacement OCO.
        stop_loss_limit_price (Decimal | None): Resolved stop-loss limit
            price, or None for a stop-market stop-loss leg.
    '''

    command_id: str
    protection_version: int
    new_list_client_order_id: str
    old_list_client_order_id: str
    take_profit_price: Decimal
    stop_loss_price: Decimal
    stop_loss_limit_price: Decimal | None = None

    def __post_init__(self) -> None:

        super().__post_init__()

        name = type(self).__name__
        _require_str(name, 'command_id', self.command_id)
        _require_str(name, 'new_list_client_order_id', self.new_list_client_order_id)
        _require_str(name, 'old_list_client_order_id', self.old_list_client_order_id)

        _require_protection_version(name, self.protection_version)

        if self.new_list_client_order_id == self.old_list_client_order_id:
            msg = f'{name} new and old list client order ids must differ'
            raise ValueError(msg)

        for field in ('take_profit_price', 'stop_loss_price', 'stop_loss_limit_price'):
            value = getattr(self, field)
            optional = field == 'stop_loss_limit_price'
            if optional and value is None:
                continue

            if not isinstance(value, Decimal) or not value.is_finite() or value <= _ZERO:
                msg = f'{name}.{field} must be a positive, finite Decimal'
                raise ValueError(msg)


@dataclass(frozen=True)
class ProtectionCancelConfirmed(_EventBase):

    '''
    Represent confirmation that the old protective OCO was cancelled.

    Written once the venue confirms the resting OCO named by the amend has
    been cancelled, so replay knows no stale protection remains before the
    replacement is placed.

    Args:
        account_id (str): Account that owns this event.
        timestamp (datetime): Event time, must be timezone-aware.
        command_id (str): Bracket command whose protective OCO is amended.
        protection_version (int): Monotonic protective-OCO revision this
            cancellation belongs to.
    '''

    command_id: str
    protection_version: int

    def __post_init__(self) -> None:

        super().__post_init__()

        name = type(self).__name__
        _require_str(name, 'command_id', self.command_id)
        _require_protection_version(name, self.protection_version)


@dataclass(frozen=True)
class ProtectionStateUnknown(_EventBase):

    '''
    Represent an ambiguous protective-OCO cancel/replace outcome.

    Written when the venue response to a cancel or replace is inconclusive
    (timeout or 5xx), so the amend halts in a known-unknown state pending
    reconciliation rather than assuming success or failure.

    Args:
        account_id (str): Account that owns this event.
        timestamp (datetime): Event time, must be timezone-aware.
        command_id (str): Bracket command whose protective OCO is amended.
        protection_version (int): Monotonic protective-OCO revision this
            ambiguity belongs to.
        reason (str): Human-readable description of the ambiguity.
        old_list_client_order_id (str | None): Pre-amend protective OCO list
            client order id, retained so the watchdog can re-query it after a
            restart. None when the amend never reached a known prior list.
        new_list_client_order_id (str | None): Replacement protective OCO list
            client order id when a replacement was submitted, retained so the
            watchdog can re-query it after a restart. None when no replacement
            was submitted.
    '''

    command_id: str
    protection_version: int
    reason: str
    old_list_client_order_id: str | None = None
    new_list_client_order_id: str | None = None

    def __post_init__(self) -> None:

        super().__post_init__()

        name = type(self).__name__
        _require_str(name, 'command_id', self.command_id)
        _require_str(name, 'reason', self.reason)
        _require_protection_version(name, self.protection_version)

        if self.old_list_client_order_id is not None:
            _require_str(
                name, 'old_list_client_order_id', self.old_list_client_order_id,
            )

        if self.new_list_client_order_id is not None:
            _require_str(
                name, 'new_list_client_order_id', self.new_list_client_order_id,
            )


@dataclass(frozen=True)
class ProtectionReplaceSubmitted(_EventBase):

    '''
    Represent submission of the replacement protective OCO, before the venue
    place.

    Persisted before the replacement OCO is placed so the replacement's list
    identity is durable and a restart mid-place cannot lose or duplicate it.

    Args:
        account_id (str): Account that owns this event.
        timestamp (datetime): Event time, must be timezone-aware.
        command_id (str): Bracket command whose protective OCO is amended.
        protection_version (int): Monotonic protective-OCO revision this
            replacement belongs to.
        new_list_client_order_id (str): Client list order id of the
            replacement OCO being placed.
    '''

    command_id: str
    protection_version: int
    new_list_client_order_id: str

    def __post_init__(self) -> None:

        super().__post_init__()

        name = type(self).__name__
        _require_str(name, 'command_id', self.command_id)
        _require_str(name, 'new_list_client_order_id', self.new_list_client_order_id)
        _require_protection_version(name, self.protection_version)


@dataclass(frozen=True)
class ProtectionActive(_EventBase):

    '''
    Represent confirmation that the replacement protective OCO is live.

    Written when the venue confirms the replacement OCO is resting, marking
    the amend complete for its revision.

    Args:
        account_id (str): Account that owns this event.
        timestamp (datetime): Event time, must be timezone-aware.
        command_id (str): Bracket command whose protective OCO is amended.
        protection_version (int): Monotonic protective-OCO revision now live.
        new_list_client_order_id (str): Client list order id of the live
            replacement OCO.
    '''

    command_id: str
    protection_version: int
    new_list_client_order_id: str

    def __post_init__(self) -> None:

        super().__post_init__()

        name = type(self).__name__
        _require_str(name, 'command_id', self.command_id)
        _require_str(name, 'new_list_client_order_id', self.new_list_client_order_id)
        _require_protection_version(name, self.protection_version)


@dataclass(frozen=True)
class ProtectionFailed(_EventBase):

    '''
    Represent that no valid protective OCO is live and remediation is needed.

    Written when the amend cannot leave a live protective OCO in place, the
    durable protection-failed marker distinct from any account operational
    mode: the position is exposed until an operator or reconciliation pass
    restores protection.

    Args:
        account_id (str): Account that owns this event.
        timestamp (datetime): Event time, must be timezone-aware.
        command_id (str): Bracket command whose protective OCO failed.
        protection_version (int): Monotonic protective-OCO revision that
            failed.
        reason (str): Human-readable description of the failure.
    '''

    command_id: str
    protection_version: int
    reason: str

    def __post_init__(self) -> None:

        super().__post_init__()

        name = type(self).__name__
        _require_str(name, 'command_id', self.command_id)
        _require_str(name, 'reason', self.reason)
        _require_protection_version(name, self.protection_version)


@dataclass(frozen=True)
class FlattenInitiated(_EventBase):

    '''
    Represent the intent to market-close a naked bracket remainder.

    Written before the MARKET flatten order is submitted to the venue, so a
    crash mid-flatten replays the intent: on restart the deterministic
    `client_order_id` is queried before any resubmission, and a live or
    filled flatten is not sent twice. The quantity is the intent-time
    reconciled remainder (recomputed and re-capped by free balance at send),
    not a promise that it is still exact.

    Args:
        account_id (str): Account that owns this event.
        timestamp (datetime): Event time, must be timezone-aware.
        command_id (str): Bracket command whose remainder is being flattened.
        protection_version (int): Protective-OCO revision whose failure
            triggered the flatten.
        qty (Decimal): Intent-time flatten quantity, a finite positive base
            amount.
        client_order_id (str): Deterministic client order id of the flatten
            MARKET order.
    '''

    command_id: str
    protection_version: int
    qty: Decimal
    client_order_id: str

    def __post_init__(self) -> None:

        super().__post_init__()

        name = type(self).__name__
        _require_str(name, 'command_id', self.command_id)
        _require_str(name, 'client_order_id', self.client_order_id)
        _require_protection_version(name, self.protection_version)

        if not isinstance(self.qty, Decimal) or not self.qty.is_finite() or self.qty <= _ZERO:
            msg = f'{name}.qty must be a finite positive Decimal'
            raise ValueError(msg)


@dataclass(frozen=True)
class ProtectionRemediationDelivered(_EventBase):

    '''
    Represent a protection remediation durably delivered to Nexus.

    Written after the account's Nexus `ProtectionRemediationHandler` has
    accepted the remediation, so a restart does not re-push a remediation an
    operator may since have cleared: the Nexus hold is sticky and
    operator-lifted, and re-pushing would re-apply it. Boot seeding skips a
    command whose remediation is already recorded delivered.

    Args:
        account_id (str): Account that owns this event.
        timestamp (datetime): Event time, must be timezone-aware.
        command_id (str): Bracket command whose remediation was delivered.
        protection_remediation_id (str): Stable id of the delivered remediation.
    '''

    command_id: str
    protection_remediation_id: str

    def __post_init__(self) -> None:

        super().__post_init__()

        name = type(self).__name__
        _require_str(name, 'command_id', self.command_id)
        _require_str(name, 'protection_remediation_id', self.protection_remediation_id)


@dataclass(frozen=True)
class OrderAmendInitiated(_EventBase):

    '''
    Represent the start of an order-price amend, before the cancel.

    Written once when a TradeModify begins amending a resting single order,
    before the cancel, so the amend is durably recorded. On boot the amend
    sequence is rebuilt from these events so a later amend cannot reuse a
    replacement client order id. Carrying the resolved replacement shape
    (old and new client ids, price, display, and the original total) keeps a
    future crash-repair that completes the re-price self-contained without
    the transient command.

    Args:
        account_id (str): Account that owns this event.
        timestamp (datetime): Event time, must be timezone-aware.
        command_id (str): Command whose resting order is amended.
        trade_id (str): Trade correlation identifier.
        symbol (str): Trading pair symbol.
        side (OrderSide): Order direction, unchanged by the amend.
        total_qty (Decimal): Original command quantity; the replacement
            works the unfilled remainder of this.
        old_client_order_id (str): Resting order being cancelled.
        new_client_order_id (str): Replacement order to place.
        price (Decimal): Resolved limit price for the replacement.
        display_qty (Decimal | None): Resolved iceberg display quantity, or
            None for a plain limit replacement.
    '''

    command_id: str
    trade_id: str
    symbol: str
    side: OrderSide
    total_qty: Decimal
    old_client_order_id: str
    new_client_order_id: str
    price: Decimal
    display_qty: Decimal | None = None

    def __post_init__(self) -> None:

        super().__post_init__()

        name = type(self).__name__
        for field in (
            'command_id',
            'trade_id',
            'symbol',
            'old_client_order_id',
            'new_client_order_id',
        ):
            _require_str(name, field, getattr(self, field))

        for field in ('total_qty', 'price'):
            value = getattr(self, field)
            if not isinstance(value, Decimal) or not value.is_finite() or value <= _ZERO:
                msg = f'{name}.{field} must be a positive, finite Decimal'
                raise ValueError(msg)

        if self.display_qty is not None and (
            not isinstance(self.display_qty, Decimal)
            or not self.display_qty.is_finite()
            or self.display_qty <= _ZERO
        ):
            msg = f'{name}.display_qty must be a positive, finite Decimal'
            raise ValueError(msg)


@dataclass(frozen=True)
class SchemeStateChanged(_EventBase):

    '''
    Represent a durable progress transition of a multi-slice scheme.

    Appended after each state transition (child submitted or filled,
    schedule advanced, hold, resume, terminal) so replay reconstructs the
    exact scheduler position on restart.

    Args:
        account_id (str): Account that owns this event.
        timestamp (datetime): Event time, must be timezone-aware.
        command_id (str): Parent scheme identifier.
        cursor (int): Next child index (slice, iteration, or level).
        filled_qty (Decimal): Cumulative filled base quantity.
        active_client_order_ids (tuple[str, ...]): Child orders currently working.
        next_run_at (datetime | None): When the next child is due, None when unscheduled.
        state (SchemeState): Lifecycle state of the scheme.
    '''

    command_id: str
    cursor: int
    filled_qty: Decimal
    active_client_order_ids: tuple[str, ...]
    next_run_at: datetime | None
    state: SchemeState

    def __post_init__(self) -> None:

        super().__post_init__()

        object.__setattr__(self, 'active_client_order_ids', tuple(self.active_client_order_ids))

        name = type(self).__name__
        _require_str(name, 'command_id', self.command_id)

        if self.cursor < 0:
            msg = f'{name}.cursor must be non-negative'
            raise ValueError(msg)

        if (
            not isinstance(self.filled_qty, Decimal)
            or not self.filled_qty.is_finite()
            or self.filled_qty < _ZERO
        ):
            msg = f'{name}.filled_qty must be a non-negative, finite Decimal'
            raise ValueError(msg)

        if self.next_run_at is not None and (
            self.next_run_at.tzinfo is None or self.next_run_at.utcoffset() is None
        ):
            msg = f'{name}.next_run_at must be timezone-aware'
            raise ValueError(msg)

        for client_order_id in self.active_client_order_ids:
            _require_str(name, 'active_client_order_ids entry', client_order_id)


@dataclass(frozen=True)
class MarkSampled(_EventBase):

    '''
    Represent a periodic mark-price sample for the metrics equity series.

    Args:
        account_id (str): Account that owns this event.
        timestamp (datetime): Sample time, must be timezone-aware.
        symbol (str): Symbol the mark applies to.
        mark_price (Decimal): Mark price at the sample, must be positive.
    '''

    symbol: str
    mark_price: Decimal

    def __post_init__(self) -> None:

        super().__post_init__()

        name = type(self).__name__
        _require_str(name, 'symbol', self.symbol)

        if not self.mark_price.is_finite() or self.mark_price <= _ZERO:
            msg = 'MarkSampled.mark_price must be a positive finite Decimal'
            raise ValueError(msg)


@dataclass(frozen=True)
class RegisterAccount(_EventBase):

    '''
    Represent registration of an account with its immutable cost-basis method.

    Args:
        account_id (str): Account that owns this event.
        timestamp (datetime): Event time, must be timezone-aware.
        cost_basis_method (str): Cost-basis method fixed for the account's
            lifetime, one of 'FIFO' or 'AVERAGE'. Defaults to 'FIFO'.
    '''

    cost_basis_method: str = CostBasisMethod.FIFO.value

    def __post_init__(self) -> None:

        super().__post_init__()

        name = type(self).__name__
        _require_str(name, 'cost_basis_method', self.cost_basis_method)

        if self.cost_basis_method not in _COST_BASIS_METHOD_VALUES:
            allowed = ', '.join(sorted(_COST_BASIS_METHOD_VALUES))
            msg = f'{name}.cost_basis_method must be one of {allowed}'
            raise ValueError(msg)


@dataclass(frozen=True)
class FundTransaction(_EventBase):

    '''
    Represent a deposit or withdrawal of quote-asset funds on an account.

    Args:
        account_id (str): Account that owns this event.
        timestamp (datetime): Event time, must be timezone-aware.
        fund_transaction_id (str): Stable unique identifier for the transaction.
        amount (Decimal): Quote-asset amount moved, must be positive and finite.
        direction (str): 'DEPOSIT' or 'WITHDRAWAL'.
    '''

    fund_transaction_id: str
    amount: Decimal
    direction: str

    def __post_init__(self) -> None:

        super().__post_init__()

        name = type(self).__name__
        _require_str(name, 'fund_transaction_id', self.fund_transaction_id)

        if not self.amount.is_finite() or self.amount <= _ZERO:
            msg = f'{name}.amount must be a positive finite Decimal'
            raise ValueError(msg)

        if self.direction not in _FUND_DIRECTION_VALUES:
            allowed = ', '.join(sorted(_FUND_DIRECTION_VALUES))
            msg = f'{name}.direction must be one of {allowed}'
            raise ValueError(msg)


@dataclass(frozen=True)
class ReconciliationMismatch(_EventBase):

    '''
    Represent a per-asset balance discrepancy found reconciling against the venue.

    Args:
        account_id (str): Account that owns this event.
        timestamp (datetime): Event time, must be timezone-aware.
        reconciliation_mismatch_id (str): Stable unique identifier for the mismatch.
        asset (str): Asset whose balance mismatched (e.g. 'USDT', 'BTC').
        expected (Decimal): Praxis-projected balance for the asset, must be finite.
        actual (Decimal): Venue-reported balance for the asset, must be finite.
    '''

    reconciliation_mismatch_id: str
    asset: str
    expected: Decimal
    actual: Decimal

    @property
    def delta(self) -> Decimal:

        '''Return the venue-reported minus Praxis-projected balance difference.'''

        return self.actual - self.expected

    def __post_init__(self) -> None:

        super().__post_init__()

        name = type(self).__name__
        _require_str(name, 'reconciliation_mismatch_id', self.reconciliation_mismatch_id)
        _require_str(name, 'asset', self.asset)

        for field_name in ('expected', 'actual'):
            value = getattr(self, field_name)
            if not isinstance(value, Decimal) or not value.is_finite():
                msg = f'{name}.{field_name} must be a finite Decimal'
                raise ValueError(msg)

        if self.expected == self.actual:
            msg = f'{name} requires expected != actual (a mismatch has a non-zero delta)'
            raise ValueError(msg)


@dataclass(frozen=True)
class OperatorHaltRequested(_EventBase):

    '''
    Represent an operator's manual request to halt trading on an account.

    Args:
        account_id (str): Account that owns this event.
        timestamp (datetime): Event time, must be timezone-aware.
        reason (str): Operator-supplied reason for the halt.
    '''

    reason: str

    def __post_init__(self) -> None:

        super().__post_init__()

        _require_str(type(self).__name__, 'reason', self.reason)


@dataclass(frozen=True)
class OperatorResumeRequested(_EventBase):

    '''
    Represent an operator's manual request to resume trading on an account.

    Args:
        account_id (str): Account that owns this event.
        timestamp (datetime): Event time, must be timezone-aware.
        reason (str): Operator-supplied reason for the resume.
    '''

    reason: str

    def __post_init__(self) -> None:

        super().__post_init__()

        _require_str(type(self).__name__, 'reason', self.reason)


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
    | BracketInitialized
    | OrderAmendInitiated
    | SchemeInitialized
    | SchemeStateChanged
    | SchemeFrozen
    | OrderSubmitIntent
    | OrderSubmitted
    | OrderSubmitFailed
    | SliceFailed
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
    | MarkSampled
    | RegisterAccount
    | FundTransaction
    | ReconciliationMismatch
    | OperatorHaltRequested
    | OperatorResumeRequested
    | ProtectionAmendRequested
    | ProtectionCancelConfirmed
    | ProtectionStateUnknown
    | ProtectionReplaceSubmitted
    | ProtectionActive
    | ProtectionFailed
    | FlattenInitiated
    | ProtectionRemediationDelivered
)
