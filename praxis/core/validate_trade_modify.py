'''
Inbound validation for TradeModify at acceptance time.

Validate command_id is known, account_id matches, the amend parameters
match the target command's execution mode, and the command is not already
terminal before enqueueing.
'''

from __future__ import annotations
from collections.abc import Set as AbstractSet

from praxis.core.domain.modify_params import MODIFY_PARAMS_FOR_MODE
from praxis.core.domain.trade_command import TradeCommand
from praxis.core.domain.trade_modify import TradeModify

__all__ = ['validate_trade_modify']


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
        ValueError: If command_id is unknown, account_id does not match, or
            the amend parameters do not match the command's execution mode.
    '''

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

    return modify.command_id not in terminal_command_ids
