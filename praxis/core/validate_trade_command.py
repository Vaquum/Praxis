'''
Inbound validation for TradeCommand at acceptance time.

Validate mode+order_type compatibility, execution_params coherence,
maker_preference constraints, and optional venue filters before
enqueueing.
'''

from __future__ import annotations

from praxis.core.domain.enums import ExecutionMode, MakerPreference, OrderType
from praxis.core.domain.trade_command import TradeCommand
from praxis.infrastructure.venue_adapter import SymbolFilters

__all__ = ['validate_trade_command']

_ALLOWED_ORDER_TYPES: dict[ExecutionMode, frozenset[OrderType]] = {
    ExecutionMode.SINGLE_SHOT: frozenset(
        {
            OrderType.MARKET,
            OrderType.LIMIT,
            OrderType.LIMIT_IOC,
            OrderType.STOP,
            OrderType.STOP_LIMIT,
            OrderType.TAKE_PROFIT,
            OrderType.TP_LIMIT,
            OrderType.OCO,
        }
    ),
    ExecutionMode.BRACKET: frozenset(
        {
            OrderType.MARKET,
            OrderType.LIMIT,
            OrderType.LIMIT_IOC,
            OrderType.STOP,
            OrderType.STOP_LIMIT,
        }
    ),
    ExecutionMode.TWAP: frozenset(
        {
            OrderType.MARKET,
            OrderType.LIMIT,
            OrderType.LIMIT_IOC,
        }
    ),
    ExecutionMode.SCHEDULED_VWAP: frozenset(
        {
            OrderType.MARKET,
            OrderType.LIMIT,
            OrderType.LIMIT_IOC,
        }
    ),
    ExecutionMode.ICEBERG: frozenset(
        {
            OrderType.LIMIT,
        }
    ),
    ExecutionMode.TIME_DCA: frozenset(
        {
            OrderType.MARKET,
            OrderType.LIMIT,
            OrderType.LIMIT_IOC,
        }
    ),
    ExecutionMode.LADDER_DCA: frozenset(
        {
            OrderType.LIMIT,
            OrderType.STOP_LIMIT,
        }
    ),
}

_PRICE_REQUIRED_TYPES: frozenset[OrderType] = frozenset(
    {
        OrderType.LIMIT,
        OrderType.LIMIT_IOC,
        OrderType.STOP_LIMIT,
        OrderType.TP_LIMIT,
        OrderType.OCO,
    }
)

_STOP_REQUIRED_TYPES: frozenset[OrderType] = frozenset(
    {
        OrderType.STOP,
        OrderType.STOP_LIMIT,
        OrderType.TAKE_PROFIT,
        OrderType.TP_LIMIT,
        OrderType.OCO,
    }
)

_STOP_LIMIT_PRICE_REQUIRED_TYPES: frozenset[OrderType] = frozenset(
    {
        OrderType.OCO,
    }
)

_MAKER_ONLY_TYPES: frozenset[OrderType] = frozenset(
    {
        OrderType.LIMIT,
        OrderType.LIMIT_IOC,
    }
)


def validate_trade_command(
    cmd: TradeCommand,
    filters: SymbolFilters | None = None,
) -> None:
    '''
    Validate a TradeCommand at acceptance time before enqueueing.

    Checks mode+order_type compatibility, execution_params coherence
    for SingleShot mode, maker_preference constraints, and optional
    venue filter compliance.

    Args:
        cmd (TradeCommand): Command to validate.
        filters (SymbolFilters | None): Optional venue filters for
            lot size, tick size, and min notional checks.

    Raises:
        ValueError: If any validation check fails.
    '''

    _validate_mode_order_type(cmd)

    if cmd.execution_mode == ExecutionMode.SINGLE_SHOT:
        _validate_single_shot_params(cmd)

    _validate_maker_preference(cmd)

    if filters is not None:
        _validate_venue_filters(cmd, filters)


def _validate_mode_order_type(cmd: TradeCommand) -> None:
    '''
    Validate order_type is allowed for the execution_mode.

    Args:
        cmd (TradeCommand): Command to validate.

    Raises:
        ValueError: If order_type is not in the allowed set for the mode.
    '''

    allowed = _ALLOWED_ORDER_TYPES.get(cmd.execution_mode)

    if allowed is None:
        msg = f"no allowed order types configured for mode {cmd.execution_mode.value}"
        raise ValueError(msg)

    if cmd.order_type not in allowed:
        msg = (
            f"{cmd.execution_mode.value} does not support "
            f"order_type {cmd.order_type.value}"
        )
        raise ValueError(msg)


def _validate_single_shot_params(cmd: TradeCommand) -> None:
    '''
    Validate execution_params coherence for SingleShot mode.

    Args:
        cmd (TradeCommand): Command with SingleShot execution_mode.

    Raises:
        ValueError: If required price fields are missing or spurious
            price fields are present.
    '''

    params = cmd.execution_params
    ot = cmd.order_type

    if ot in _PRICE_REQUIRED_TYPES and params.price is None:
        msg = f"{ot.value} requires execution_params.price"
        raise ValueError(msg)

    if ot not in _PRICE_REQUIRED_TYPES and params.price is not None:
        msg = f"{ot.value} does not use execution_params.price"
        raise ValueError(msg)

    if ot in _STOP_REQUIRED_TYPES and params.stop_price is None:
        msg = f"{ot.value} requires execution_params.stop_price"
        raise ValueError(msg)

    if ot not in _STOP_REQUIRED_TYPES and params.stop_price is not None:
        msg = f"{ot.value} does not use execution_params.stop_price"
        raise ValueError(msg)

    if ot in _STOP_LIMIT_PRICE_REQUIRED_TYPES and params.stop_limit_price is None:
        msg = f"{ot.value} requires execution_params.stop_limit_price"
        raise ValueError(msg)

    if (
        ot not in _STOP_LIMIT_PRICE_REQUIRED_TYPES
        and params.stop_limit_price is not None
    ):
        msg = f"{ot.value} does not use execution_params.stop_limit_price"
        raise ValueError(msg)


def _validate_maker_preference(cmd: TradeCommand) -> None:
    '''
    Validate maker_preference is compatible with order_type.

    Args:
        cmd (TradeCommand): Command to validate.

    Raises:
        ValueError: If MAKER_ONLY is set with an incompatible order_type.
    '''

    if cmd.maker_preference != MakerPreference.MAKER_ONLY:
        return

    if cmd.order_type not in _MAKER_ONLY_TYPES:
        msg = (
            f"MAKER_ONLY requires order_type in "
            f"{{LIMIT, LIMIT_IOC}}, got {cmd.order_type.value}"
        )
        raise ValueError(msg)


def _validate_venue_filters(
    cmd: TradeCommand,
    filters: SymbolFilters,
) -> None:
    '''
    Validate command against venue-imposed trading filters.

    Args:
        cmd (TradeCommand): Command to validate.
        filters (SymbolFilters): Venue filters for the symbol.

    Raises:
        ValueError: If qty or price violates venue filters.
    '''

    if cmd.qty % filters.lot_step != 0:
        msg = f"qty {cmd.qty} is not a multiple of lot step {filters.lot_step}"
        raise ValueError(msg)

    if cmd.qty < filters.lot_min:
        msg = f"qty {cmd.qty} is below lot minimum {filters.lot_min}"
        raise ValueError(msg)

    if cmd.qty > filters.lot_max:
        msg = f"qty {cmd.qty} is above lot maximum {filters.lot_max}"
        raise ValueError(msg)

    price = cmd.execution_params.price

    if price is not None and cmd.order_type != OrderType.MARKET:
        if price % filters.tick_size != 0:
            msg = f"price {price} is not a multiple of tick size {filters.tick_size}"
            raise ValueError(msg)

        if price * cmd.qty < filters.min_notional:
            msg = f"notional {price * cmd.qty} is below minimum {filters.min_notional}"
            raise ValueError(msg)
