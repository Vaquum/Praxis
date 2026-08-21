'''
Inbound validation for TradeModify at acceptance time.

Validate command_id is known, account_id matches, and the amend parameters
match the target command's execution mode before enqueueing. A terminal
command is normally a no-op, with one exception: a bracket whose entry has
filled (terminal) but whose protective OCO is still live and amendable is
resolved through `bracket_commands` and admitted.
'''

from __future__ import annotations
from collections.abc import Sequence, Set as AbstractSet
from decimal import Decimal

from praxis.core.domain.enums import ExecutionMode, OrderSide
from praxis.core.domain.ladder_dca_modify import LadderDcaModify
from praxis.core.domain.ladder_dca_params import LadderDcaParams
from praxis.core.domain.modify_params import MODIFY_PARAMS_FOR_MODE
from praxis.core.domain.trade_command import TradeCommand
from praxis.core.domain.trade_modify import TradeModify

__all__ = ['validate_trade_modify']

_CEILING_PRICE_FIELDS: dict[ExecutionMode, tuple[str, ...]] = {
    ExecutionMode.SINGLE_SHOT: ('price', 'stop_limit_price'),
    ExecutionMode.ICEBERG: ('limit_price',),
}


def _weighted_price_sum(
    prices: Sequence[Decimal], weights: Sequence[Decimal] | None,
) -> Decimal:
    '''Return the per-unit quote commitment of a ladder grid.

    The quote committed per unit of base is the quantity-weighted average
    rung price; with weights absent the quantity splits equally, so each rung
    carries `1/N`. Multiplying by the (unchanged) command quantity gives total
    quote exposure, so this per-unit sum is a sufficient comparison basis.
    '''

    if weights is None:
        equal = Decimal(1) / Decimal(len(prices))
        return sum((price * equal for price in prices), Decimal(0))

    return sum(
        (price * weight for price, weight in zip(prices, weights, strict=False)),
        Decimal(0),
    )


def _ladder_amend_raises_exposure(
    modify: LadderDcaModify, params: LadderDcaParams,
) -> bool:
    '''Return True when a ladder amend raises BUY quote commitment.

    A ladder commits quote as the quantity-weighted sum of rung prices, so a
    weight-only amend that shifts quantity onto higher rungs raises exposure
    with no changed price field. Both prices and weights are resolved (amended
    value or original) and the weighted commitment compared; a rung-count
    change that leaves the weighted price sum incomparable is a conservative
    increase.
    '''

    new_prices = (
        modify.price_levels if modify.price_levels is not None else params.price_levels
    )
    new_weights = (
        modify.level_weights if modify.level_weights is not None
        else params.level_weights
    )

    if new_weights is not None and len(new_weights) != len(new_prices):
        return True

    return _weighted_price_sum(new_prices, new_weights) > _weighted_price_sum(
        params.price_levels, params.level_weights,
    )


def _amend_raises_buy_exposure(modify: TradeModify, command: TradeCommand) -> bool:  # noqa: PLR0911
    '''Return True when a BUY amend would lift quote exposure above the original.

    Quote exposure on a BUY limit order is price times base quantity; base
    quantity is not amendable, so any amended commitment price above the
    original raises the quote committed for the same quantity beyond what the
    entry reserved. Only commitment prices are checked (the limit price, the
    stop-limit price) — a stop trigger does not itself set the committed quote.
    A ladder commits the quantity-weighted sum of its rung prices, so a
    price-or-weight amend is compared by weighted commitment. A SELL commits
    base it already holds, so its price amends never raise quote exposure.
    Conservative: an amended price with no original to bound it against, or a
    ladder re-weighted to an incomparable rung count, is treated as an increase.
    '''

    if command.side is not OrderSide.BUY:
        return False

    if (
        command.execution_mode is ExecutionMode.LADDER_DCA
        and isinstance(modify.modify_params, LadderDcaModify)
        and isinstance(command.execution_params, LadderDcaParams)
    ):
        return _ladder_amend_raises_exposure(
            modify.modify_params, command.execution_params,
        )

    for field in _CEILING_PRICE_FIELDS.get(command.execution_mode, ()):
        new_value = getattr(modify.modify_params, field, None)

        if new_value is None:
            continue

        original = getattr(command.execution_params, field, None)

        if original is None:
            return True

        if isinstance(new_value, tuple):
            if len(new_value) != len(original):
                return True

            if any(new > old for new, old in zip(new_value, original, strict=True)):
                return True

        elif new_value > original:
            return True

    return False


def validate_trade_modify(
    modify: TradeModify,
    commands: dict[str, TradeCommand],
    terminal_command_ids: AbstractSet[str],
    bracket_commands: dict[str, TradeCommand] | None = None,
) -> bool:
    '''
    Validate a TradeModify at acceptance time before enqueueing.

    A terminal command is normally a no-op — its execution is done. The one
    exception is a bracket whose entry has filled (terminal) but whose
    protective OCO is still live and amendable: `bracket_commands` maps such
    entry command ids to their bracket `TradeCommand`, so an amend addressed
    to the entry id resolves to the live protection instead of being dropped.
    The entry is gone from `commands` (popped on its terminal outcome), so
    the bracket command is the sole source for the mode / account check.

    Args:
        modify (TradeModify): Amend instruction to validate.
        commands (dict[str, TradeCommand]): Mapping of command_id to the
            accepted TradeCommand, used to check the owning account and the
            execution mode being amended.
        terminal_command_ids (AbstractSet[str]): Set of command_ids that
            have reached a terminal state.
        bracket_commands (dict[str, TradeCommand] | None): Entry command ids
            whose bracket protection is live and amendable, mapped to the
            bracket command. A terminal entry present here is amendable.

    Returns:
        bool: True if the amend should be enqueued, False if the target
            command is terminal with no live amendable protection (no-op).

    Raises:
        ValueError: If command_id is unknown, account_id does not match, the
            amend parameters do not match the command's execution mode, or a
            BUY amend would raise quote exposure above the original commitment.
    '''

    if modify.command_id in terminal_command_ids:
        command = (bracket_commands or {}).get(modify.command_id)

        if command is None:
            return False

    else:
        command = commands.get(modify.command_id)

        if command is None:
            msg = f"unknown command_id '{modify.command_id}'"
            raise ValueError(msg)

    if modify.account_id != command.account_id:
        msg = (
            f"account_id mismatch: modify has '{modify.account_id}', "
            f"command belongs to '{command.account_id}'"
        )
        raise ValueError(msg)

    expected = MODIFY_PARAMS_FOR_MODE[command.execution_mode]

    if not isinstance(modify.modify_params, expected):
        msg = (
            f'modify_params {type(modify.modify_params).__name__} does not '
            f'match execution mode {command.execution_mode.value}'
        )
        raise ValueError(msg)

    if _amend_raises_buy_exposure(modify, command):
        msg = (
            f"amend raises buy-side quote exposure above the original "
            f"commitment for command_id '{modify.command_id}'; place a new "
            f"order to increase exposure"
        )
        raise ValueError(msg)

    return True
