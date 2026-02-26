'''
Validate that a string field is non-empty.

Shared validation helper used across all domain dataclasses
to enforce non-empty string invariants at construction time.
'''

from __future__ import annotations

__all__ = ['_require_str']


def _require_str(cls: str, field: str, value: str | None, *, optional: bool = False) -> None:

    '''
    Validate that a string field is non-empty.

    Args:
        cls (str): Class name for error context.
        field (str): Field name for error context.
        value (str | None): Value to validate.
        optional (bool): Allow None values when True.
    '''

    if value is None and optional:
        return

    if not value:
        msg = f'{cls}.{field} must be a non-empty string'
        raise ValueError(msg)
