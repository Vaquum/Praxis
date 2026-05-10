'''Translate Nexus-shape command payloads into Praxis domain types.

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

Nexus and Praxis also each define their own copies of the order-shape
enums (`OrderSide`, `OrderType`, `ExecutionMode`, `MakerPreference`,
`STPMode`). Even when the string `.value` payloads agree, the two
enum classes are distinct Python objects, so any identity- or
hash-based check on the Praxis side (`_ALLOWED_ORDER_TYPES.get(...)`,
`execution_mode is ExecutionMode.SINGLE_SHOT`, dataclass field
isinstance enforcement) silently fails when handed a Nexus member.
The `translate_*` helpers re-key each Nexus enum to the equivalent
Praxis member by `.value`, so the Praxis validator and dataclass
invariants see their own type. `STPMode` is the one enum where the
two sides do not share value strings (Nexus uses `CANCEL_*`, Praxis
uses `EXPIRE_*`); `_STP_MODE_VALUE_MAP` records the semantic
equivalence so the translation does not silently drop the value.
'''

from __future__ import annotations

from collections.abc import Mapping
from decimal import Decimal
from enum import Enum

from praxis.core.domain.enums import (
    ExecutionMode,
    MakerPreference,
    OrderSide,
    OrderType,
    STPMode,
)
from praxis.core.domain.single_shot_params import SingleShotParams

__all__ = [
    'build_single_shot_params',
    'translate_execution_mode',
    'translate_maker_preference',
    'translate_order_side',
    'translate_order_type',
    'translate_stp_mode',
]

_ALLOWED_KEYS = frozenset({'price', 'stop_price', 'stop_limit_price'})

_STP_MODE_VALUE_MAP: dict[str, str] = {
    'CANCEL_MAKER': 'EXPIRE_MAKER',
    'CANCEL_TAKER': 'EXPIRE_TAKER',
    'CANCEL_BOTH': 'EXPIRE_BOTH',
}

def _translate_enum[E: Enum](
    value: object,
    praxis_enum_cls: type[E],
    field_name: str,
    value_map: Mapping[str, str] | None = None,
) -> E:
    if isinstance(value, praxis_enum_cls):
        return value
    raw = getattr(value, 'value', None)
    if not isinstance(raw, str):
        msg = (
            f'{field_name} must be {praxis_enum_cls.__name__} or an '
            f'enum with a string .value, got {type(value).__name__}'
        )
        raise TypeError(msg)
    mapped = value_map[raw] if value_map is not None and raw in value_map else raw
    try:
        return praxis_enum_cls(mapped)
    except ValueError as exc:
        msg = (
            f'{field_name} value {raw!r} has no '
            f'{praxis_enum_cls.__name__} equivalent'
        )
        raise ValueError(msg) from exc


def translate_order_side(value: object) -> OrderSide:
    '''Re-key a foreign `OrderSide` to the Praxis `OrderSide` member.'''

    return _translate_enum(value, OrderSide, 'side')


def translate_order_type(value: object) -> OrderType:
    '''Re-key a foreign `OrderType` to the Praxis `OrderType` member.'''

    return _translate_enum(value, OrderType, 'order_type')


def translate_execution_mode(value: object) -> ExecutionMode:
    '''Re-key a foreign `ExecutionMode` to the Praxis member.'''

    return _translate_enum(value, ExecutionMode, 'execution_mode')


def translate_maker_preference(value: object) -> MakerPreference:
    '''Re-key a foreign `MakerPreference` to the Praxis member.'''

    return _translate_enum(value, MakerPreference, 'maker_preference')


def translate_stp_mode(value: object) -> STPMode:
    '''Re-key a foreign `STPMode` to the Praxis member.

    The two enums use different value strings (Nexus `CANCEL_*` vs
    Praxis `EXPIRE_*`); `_STP_MODE_VALUE_MAP` records the semantic
    equivalence used during translation.
    '''

    return _translate_enum(value, STPMode, 'stp_mode', _STP_MODE_VALUE_MAP)


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
