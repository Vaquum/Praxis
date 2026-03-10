'''
Inbound validation for TradeAbort at acceptance time.

Validate command_id is known, account_id matches, and command is not
already terminal before enqueueing.
'''

from __future__ import annotations

from praxis.core.domain.trade_abort import TradeAbort

__all__ = ['validate_trade_abort']


def validate_trade_abort(
    abort: TradeAbort,
    accepted_commands: dict[str, str],
    terminal_command_ids: frozenset[str],
) -> bool:
    '''
    Validate a TradeAbort at acceptance time before enqueueing.

    Args:
        abort (TradeAbort): Abort instruction to validate.
        accepted_commands (dict[str, str]): Mapping of command_id to
            account_id for all accepted commands.
        terminal_command_ids (frozenset[str]): Set of command_ids that
            have reached a terminal state.

    Returns:
        bool: True if the abort should be enqueued, False if the
            target command is already terminal (no-op per RFC).

    Raises:
        ValueError: If command_id is unknown or account_id does not
            match the original command.
    '''

    owner = accepted_commands.get(abort.command_id)

    if owner is None:
        msg = f"unknown command_id '{abort.command_id}'"
        raise ValueError(msg)

    if abort.command_id in terminal_command_ids:
        return False

    if abort.account_id != owner:
        msg = (
            f"account_id mismatch: abort has '{abort.account_id}', "
            f"command belongs to '{owner}'"
        )
        raise ValueError(msg)

    return True
