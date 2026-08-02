'''
Deterministic exit command id for a bracket's protective OCO.

A bracket reports its entry outcome under the entry command id; the
protective OCO's position-closing fill reports under the derived exit id
from `bracket_exit_command_id`. Nexus derives the same id when it
dispatches the bracket, so it can pre-register the protective exit and
reduce the position when the exit outcome arrives — no round-trip needed.
The derivation is the cross-repo contract: both sides must compute it
identically.
'''

from __future__ import annotations

__all__ = ['BRACKET_EXIT_COMMAND_SUFFIX', 'bracket_exit_command_id']

BRACKET_EXIT_COMMAND_SUFFIX = 'x'


def bracket_exit_command_id(command_id: str) -> str:
    '''Derive the deterministic exit command id for a bracket entry.

    Args:
        command_id (str): The bracket entry command id.

    Returns:
        str: The protective-exit command id, the entry id suffixed with
            `-{BRACKET_EXIT_COMMAND_SUFFIX}`.
    '''

    return f'{command_id}-{BRACKET_EXIT_COMMAND_SUFFIX}'
