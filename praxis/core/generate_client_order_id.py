'''
Deterministic client order ID generation for venue order submission.

Produce a compact, deterministic string from execution mode, command ID,
sequence index, and retry count. Format: ``{prefix}-{hex16}-{seq}[rN]``.
'''

from __future__ import annotations

from praxis.core.domain.enums import ExecutionMode

__all__ = ['generate_client_order_id']

_MAX_LENGTH = 36
_MAX_SEQUENCE = 999

_MODE_PREFIX: dict[ExecutionMode, str] = {
    ExecutionMode.SINGLE_SHOT: 'SS',
    ExecutionMode.BRACKET: 'BK',
    ExecutionMode.TWAP: 'TW',
    ExecutionMode.SCHEDULED_VWAP: 'SV',
    ExecutionMode.ICEBERG: 'IC',
    ExecutionMode.TIME_DCA: 'TD',
    ExecutionMode.LADDER_DCA: 'LD',
}

_CMD_ID_HEX_LENGTH = 16


def generate_client_order_id(
    mode: ExecutionMode,
    command_id: str,
    sequence: int,
    retry: int = 0,
) -> str:
    '''
    Compute a deterministic client order ID for venue submission.

    Args:
        mode (ExecutionMode): Execution strategy determining the prefix
        command_id (str): UUID4 command identifier to truncate
        sequence (int): Zero-based slice, iteration, or level index
        retry (int): Retry attempt number, 0 for first attempt

    Returns:
        str: Client order ID of at most 36 characters

    Raises:
        ValueError: If mode has no prefix, command_id too short, sequence or retry out of range, or result exceeds 36 characters
    '''

    if mode not in _MODE_PREFIX:
        msg = f'no prefix defined for execution mode: {mode!r}'
        raise ValueError(msg)

    if sequence < 0 or sequence > _MAX_SEQUENCE:
        msg = f'sequence must be between 0 and {_MAX_SEQUENCE}'
        raise ValueError(msg)

    if retry < 0:
        msg = 'retry must be non-negative'
        raise ValueError(msg)

    prefix = _MODE_PREFIX[mode]
    cmd_hex = command_id.replace('-', '')[:_CMD_ID_HEX_LENGTH]
    if len(cmd_hex) < _CMD_ID_HEX_LENGTH:
        msg = f'command_id must contain at least {_CMD_ID_HEX_LENGTH} hex characters after stripping hyphens'
        raise ValueError(msg)
    seq_str = f'{sequence:03d}'
    retry_str = f'r{retry}' if retry > 0 else ''

    result = f'{prefix}-{cmd_hex}-{seq_str}{retry_str}'

    if len(result) > _MAX_LENGTH:
        msg = f'client order ID exceeds {_MAX_LENGTH} characters: {result!r}'
        raise ValueError(msg)

    return result
