'''
Deterministic client order ID generation for venue order submission.

Produce a compact, deterministic string from execution mode, command ID,
sequence index, and retry count. Format: ``{prefix}-{hex16}-{seq}[rN]``.
'''

from __future__ import annotations

import re

from praxis.core.domain.enums import ExecutionMode

__all__ = [
    'command_id_fragment',
    'generate_client_order_id',
    'praxis_command_fragment',
    'validate_command_id_for_client_order_id',
]

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

_PRAXIS_CLIENT_ORDER_ID_RE = re.compile(
    '^(?:'
    + '|'.join(sorted(set(_MODE_PREFIX.values())))
    + f')-(?P<fragment>[^-]{{{_CMD_ID_HEX_LENGTH}}})-\\d{{3}}(?:r\\d+)?$'
)


def command_id_fragment(command_id: str) -> str:
    '''Compute the command fragment `generate_client_order_id` embeds.

    A client order ID carries the first `_CMD_ID_HEX_LENGTH` characters of
    the hyphen-stripped command ID. This is the sole slice tying a venue
    order back to the command that produced it.

    Args:
        command_id: The command identifier.

    Returns:
        str: The embedded command fragment.
    '''

    return command_id.replace('-', '')[:_CMD_ID_HEX_LENGTH]


def praxis_command_fragment(client_order_id: str) -> str | None:
    '''Extract the command fragment a Praxis client order ID embeds.

    A venue order carries a Praxis command fragment only if its client
    order ID matches the `{prefix}-{fragment}-{seq}[rN]` grammar that
    `generate_client_order_id` produces — a prefix drawn from
    `_MODE_PREFIX`, then any 16 non-hyphen command characters, then the
    zero-padded sequence and optional retry. The returned fragment is
    matched against the account's accepted commands to decide ownership;
    on its own the shape is not proof of ownership, since an external
    order could imitate it.

    Args:
        client_order_id: The venue order's client order ID.

    Returns:
        str | None: The embedded command fragment, or `None` if the ID
            does not match Praxis's minting grammar.
    '''

    match = _PRAXIS_CLIENT_ORDER_ID_RE.match(client_order_id)
    if match is None:
        return None

    return match.group('fragment')


def validate_command_id_for_client_order_id(command_id: str) -> None:
    '''Validate that `command_id` can derive a client order ID.

    `generate_client_order_id` slices the hyphen-stripped command_id to
    `_CMD_ID_HEX_LENGTH` characters; an id shorter than that after
    stripping cannot produce a valid client order ID. Callers that
    accept caller-supplied ids should run this at their inbound
    boundary so a too-short id is rejected before any state is
    persisted, rather than failing later at submission.

    Args:
        command_id: The command identifier to validate.

    Raises:
        ValueError: If `command_id` has fewer than
            `_CMD_ID_HEX_LENGTH` characters after stripping hyphens.
    '''

    if len(command_id.replace('-', '')) < _CMD_ID_HEX_LENGTH:
        msg = (
            f'command_id must have at least {_CMD_ID_HEX_LENGTH} '
            'characters after stripping hyphens'
        )
        raise ValueError(msg)


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
        msg = f"no prefix defined for execution mode: {mode!r}"
        raise ValueError(msg)

    if sequence < 0 or sequence > _MAX_SEQUENCE:
        msg = f"sequence must be between 0 and {_MAX_SEQUENCE}"
        raise ValueError(msg)

    if retry < 0:
        msg = 'retry must be non-negative'
        raise ValueError(msg)

    validate_command_id_for_client_order_id(command_id)

    prefix = _MODE_PREFIX[mode]
    cmd_hex = command_id_fragment(command_id)
    seq_str = f"{sequence:03d}"
    retry_str = f"r{retry}" if retry > 0 else ''

    result = f"{prefix}-{cmd_hex}-{seq_str}{retry_str}"

    if len(result) > _MAX_LENGTH:
        msg = f"client order ID exceeds {_MAX_LENGTH} characters: {result!r}"
        raise ValueError(msg)

    return result
