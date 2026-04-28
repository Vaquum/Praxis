'''Translate Nexus-shape `execution_params` payloads into Praxis types.

The Nexus `TradeCommand.execution_params` field is typed as
`Mapping[str, object] | None` so strategies can ship plain dicts or
omit it entirely. Praxis `Trading.submit_command` enforces
`isinstance(execution_params, SingleShotParams)` for SINGLE_SHOT mode
and raises `TypeError` otherwise. The mismatch sits exactly on the
Praxis -> Nexus seam; bridging it on the Praxis side keeps Nexus
free of Praxis-domain imports.

`build_single_shot_params` accepts the three shapes Nexus may send
(`None`, `Mapping`, or `SingleShotParams` — the last passes through
untouched) and returns a validated `SingleShotParams`. Unknown keys
raise rather than silently drop, so a strategy bug surfaces fast.
'''

from __future__ import annotations

from collections.abc import Mapping
from decimal import Decimal

from praxis.core.domain.single_shot_params import SingleShotParams

__all__ = ['build_single_shot_params']

_ALLOWED_KEYS = frozenset({'price', 'stop_price', 'stop_limit_price'})


def build_single_shot_params(
    value: SingleShotParams | Mapping[str, object] | None,
) -> SingleShotParams:

    '''Coerce a Nexus `execution_params` payload into `SingleShotParams`.

    Args:
        value: The `execution_params` field from a Nexus `TradeCommand`.
            One of:
              * `None` — market-order shape, all price fields default to None
              * `Mapping[str, object]` — keys among `price`, `stop_price`,
                `stop_limit_price`; values must be `Decimal` or `None`
              * `SingleShotParams` — passed through unchanged

    Returns:
        A `SingleShotParams` instance accepted by `Trading.submit_command`.

    Raises:
        TypeError: If `value` is not one of the three accepted shapes,
            or if any value is not a `Decimal`.
        ValueError: If any key is outside the allowed set, or if
            `SingleShotParams.__post_init__` rejects a non-positive value.
    '''

    if isinstance(value, SingleShotParams):
        return value

    if value is None:
        return SingleShotParams()

    if not isinstance(value, Mapping):
        msg = (
            'execution_params must be None, Mapping, or SingleShotParams, '
            f'got {type(value).__name__}'
        )
        raise TypeError(msg)

    unknown = set(value.keys()) - _ALLOWED_KEYS
    if unknown:
        msg = (
            'execution_params has unsupported keys for SINGLE_SHOT: '
            f'{sorted(unknown)} (allowed: {sorted(_ALLOWED_KEYS)})'
        )
        raise ValueError(msg)

    kwargs: dict[str, Decimal | None] = {}
    for key in _ALLOWED_KEYS:
        raw = value.get(key)
        if raw is None:
            kwargs[key] = None
            continue
        if not isinstance(raw, Decimal):
            msg = (
                f'execution_params[{key!r}] must be Decimal or None, '
                f'got {type(raw).__name__}'
            )
            raise TypeError(msg)
        kwargs[key] = raw

    return SingleShotParams(**kwargs)
