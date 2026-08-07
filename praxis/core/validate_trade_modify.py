'''
Inbound validation for TradeModify at acceptance time.

Validate command_id is known, account_id matches, the amend parameters
match the target command's execution mode, and the command is not already
terminal before enqueueing.
'''

from __future__ import annotations
from collections.abc import Set as AbstractSet

from praxis.core.domain.enums import ExecutionMode, OrderSide
from praxis.core.domain.modify_params import MODIFY_PARAMS_FOR_MODE
from praxis.core.domain.trade_command import TradeCommand
from praxis.core.domain.trade_modify import TradeModify

__all__ = ['validate_trade_modify']

_CEILING_PRICE_FIELDS: dict[ExecutionMode, tuple[str, ...]] = {
    ExecutionMode.SINGLE_SHOT: ('price', 'stop_limit_price'),
    ExecutionMode.ICEBERG: ('limit_price',),
    ExecutionMode.LADDER_DCA: ('price_levels',),
}


def _amend_raises_buy_exposure(modify: TradeModify, command: TradeCommand) -> bool:
    '''Return True when a BUY amend would lift quote exposure above the original.

    Quote exposure on a BUY limit order is price times base quantity; base
    quantity is not amendable, so any amended commitment price above the
    original raises the quote committed for the same quantity beyond what the
    entry reserved. Only commitment prices are checked (the limit price, the
    stop-limit price, ladder rung prices) — a stop trigger does not itself set
    the committed quote. A SELL commits base it already holds, so its price
    amends never raise quote exposure. Conservative: an amended price with no
    original to bound it against, or a ladder re-priced to a different rung
    count, is treated as an increase.
    '''

    if command.side is not OrderSide.BUY:
        return False

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
) -> bool:
    '''
    Validate a TradeModify at acceptance time before enqueueing.

    Args:
        modify (TradeModify): Amend instruction to validate.
        commands (dict[str, TradeCommand]): Mapping of command_id to the
            accepted TradeCommand, used to check the owning account and the
            execution mode being amended.
        terminal_command_ids (AbstractSet[str]): Set of command_ids that
            have reached a terminal state.

    Returns:
        bool: True if the amend should be enqueued, False if the target
            command is already terminal (no-op).

    Raises:
        ValueError: If command_id is unknown, account_id does not match, the
            amend parameters do not match the command's execution mode, or a
            BUY amend would raise quote exposure above the original commitment.
    '''

    if modify.command_id in terminal_command_ids:
        return False

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

    return modify.command_id not in terminal_command_ids
