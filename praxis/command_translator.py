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

`build_execution_params` extends this to every execution mode, and
`build_modify_params` does the same for amends. Both resolve the mode's
dataclass through the canonical registries (`PARAMS_FOR_MODE`,
`MODIFY_PARAMS_FOR_MODE`) and derive from it the keys the payload may carry
and the fields whose list payloads coerce to tuples, so a mode is wired up
by registering its params type alone — there is no second per-mode table
here to drift from the dataclass it mirrors. Keys outside the mode's field
set are rejected. SINGLE_SHOT keeps `build_single_shot_params` — it alone
accepts an omitted (`None`) payload and type-checks Decimals directly; the
other modes self-validate in their dataclass `__post_init__`.
'''

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import fields
from decimal import Decimal
from enum import Enum
from types import UnionType
from typing import Annotated, Any, Union, get_args, get_origin, get_type_hints

from praxis.core.domain.enums import (
    ExecutionMode,
    MakerPreference,
    OrderSide,
    OrderType,
    STPMode,
)
from praxis.core.domain.execution_params import PARAMS_FOR_MODE, ExecutionParams
from praxis.core.domain.modify_params import MODIFY_PARAMS_FOR_MODE, ModifyParams
from praxis.core.domain.single_shot_params import SingleShotParams

__all__ = [
    'build_execution_params',
    'build_modify_params',
    'build_single_shot_params',
    'translate_execution_mode',
    'translate_maker_preference',
    'translate_order_side',
    'translate_order_type',
    'translate_stp_mode',
]


def _field_names(cls: type) -> frozenset[str]:

    '''Return the constructor-settable field names of a params dataclass.

    Non-init fields are excluded: they cannot be passed to the dataclass
    constructor, so they are not part of the payload's wire shape.
    '''

    return frozenset(field.name for field in fields(cls) if field.init)


def _is_tuple_hint(hint: object) -> bool:

    '''Whether a type hint is a tuple, including inside a union.

    Recursion walks unions only, so a tuple nested in some other generic
    (`list[tuple[int, ...]]`) is not mistaken for a tuple field whose list
    payload should be coerced.
    '''

    hint = _unwrap_annotated(hint)

    if hint is tuple or get_origin(hint) is tuple:
        return True

    if get_origin(hint) in (Union, UnionType):
        return any(_is_tuple_hint(arg) for arg in get_args(hint))

    return False


def _unwrap_annotated(hint: object) -> object:

    '''Strip `Annotated[...]` down to the type it wraps.'''

    while get_origin(hint) is Annotated:
        hint = get_args(hint)[0]

    return hint


def _tuple_field_names(cls: type) -> frozenset[str]:

    '''Return the tuple-typed constructor field names of a params dataclass.

    A Nexus payload ships JSON arrays for these, so `_build_from_mapping`
    coerces the list to the tuple the dataclass declares.
    '''

    hints = get_type_hints(cls)

    return frozenset(
        field.name
        for field in fields(cls)
        if field.init and _is_tuple_hint(hints[field.name])
    )


# Derived once at import from the two canonical registries, so a params
# dataclass and the payload keys accepted for its mode cannot drift, and an
# unresolvable annotation fails at import rather than on the first command.
_PARAMS_CLASSES: tuple[type, ...] = (
    *PARAMS_FOR_MODE.values(),
    *MODIFY_PARAMS_FOR_MODE.values(),
)
_FIELD_NAMES: dict[type, frozenset[str]] = {
    cls: _field_names(cls) for cls in _PARAMS_CLASSES
}
_TUPLE_FIELD_NAMES: dict[type, frozenset[str]] = {
    cls: _tuple_field_names(cls) for cls in _PARAMS_CLASSES
}

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
    '''Re-key a foreign `MakerPreference` to the Praxis member.

    `None` substitutes to `MakerPreference.NO_PREFERENCE`: Nexus's
    [`Action`](https://github.com/Vaquum/Nexus/blob/v0.46.0/nexus/strategy/action.py)
    dataclass declares `maker_preference: MakerPreference | None = None`
    and only validates the type when the field is set, so any Nexus
    strategy that omits `maker_preference` ships `None` through to the
    Praxis seam. Pre-v0.58.0 the Praxis `validate_trade_command`
    short-circuited on `cmd.maker_preference != MakerPreference.MAKER_ONLY`
    and `None` flowed through harmlessly. Substituting `NO_PREFERENCE`
    here keeps the historical "no opinion" semantics while letting the
    Praxis dataclass and validator see a real enum (so the type
    contract on `Trading.submit_command` is honest end-to-end).
    '''

    if value is None:
        return MakerPreference.NO_PREFERENCE
    return _translate_enum(value, MakerPreference, 'maker_preference')


def translate_stp_mode(value: object) -> STPMode:
    '''Re-key a foreign `STPMode` to the Praxis member.

    The two enums use different value strings (Nexus `CANCEL_*` vs
    Praxis `EXPIRE_*`); `_STP_MODE_VALUE_MAP` records the semantic
    equivalence used during translation. `None` substitutes to
    `STPMode.NONE`: Nexus's
    [`translate_to_trade_command`](https://github.com/Vaquum/Nexus/blob/v0.46.0/nexus/infrastructure/praxis_connector/translate.py)
    sets `stp_mode=None` for AMEND / CANCEL paths, and Praxis stores
    the field on `TradeCommand` without ever reading it at the venue
    boundary, so `None` had no observable effect pre-v0.58.0.
    Substituting `STPMode.NONE` keeps the type contract honest while
    preserving the existing zero-effect behaviour.
    '''

    if value is None:
        return STPMode.NONE
    return _translate_enum(value, STPMode, 'stp_mode', _STP_MODE_VALUE_MAP)


def build_single_shot_params(
    value: object,
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

    allowed_keys = _FIELD_NAMES[SingleShotParams]
    unknown = set(value.keys()) - allowed_keys
    if unknown:
        msg = (
            'execution_params has unsupported keys for SINGLE_SHOT: '
            f'{sorted(unknown)} (allowed: {sorted(allowed_keys)})'
        )
        raise ValueError(msg)

    kwargs: dict[str, Decimal | None] = {}
    for key in allowed_keys:
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


def _build_from_mapping[P](
    cls: type[P],
    value: object,
    mode_label: str,
    allowed_keys: frozenset[str],
    tuple_keys: frozenset[str] = frozenset(),
    payload_label: str = 'execution_params',
) -> P:

    '''Build a per-mode params dataclass from a Nexus payload mapping.

    Args:
        cls: The target params dataclass.
        value: The payload — a `cls` instance (passed through) or a
            `Mapping` of its field names.
        mode_label: Execution-mode name for error messages.
        allowed_keys: Field names accepted for this mode.
        tuple_keys: Field names whose list payloads are coerced to tuples.
        payload_label: Payload field name for error messages
            (`execution_params` or `modify_params`).

    Returns:
        A validated `cls` instance.

    Raises:
        TypeError: If `value` is neither a `cls` instance nor a `Mapping`.
        ValueError: If the mapping carries a key outside `allowed_keys`, or
            if the dataclass rejects the values.
    '''

    if isinstance(value, cls):
        return value

    if not isinstance(value, Mapping):
        msg = (
            f'{payload_label} for {mode_label} must be {cls.__name__} or a '
            f'Mapping, got {type(value).__name__}'
        )
        raise TypeError(msg)

    unknown = set(value.keys()) - allowed_keys
    if unknown:
        msg = (
            f'{payload_label} has unsupported keys for {mode_label}: '
            f'{sorted(unknown)} (allowed: {sorted(allowed_keys)})'
        )
        raise ValueError(msg)

    kwargs: dict[str, Any] = {}
    for key, raw in value.items():
        kwargs[key] = tuple(raw) if key in tuple_keys and isinstance(raw, list) else raw

    return cls(**kwargs)


def build_execution_params(
    mode: ExecutionMode,
    value: object,
) -> ExecutionParams:

    '''Coerce a Nexus `execution_params` payload into the mode's params type.

    Dispatches on `mode` to the matching params dataclass, validating the
    payload's keys and values. A dataclass instance passes through; a
    `Mapping` is built into the dataclass; any other shape fails closed.

    Args:
        mode: The command's execution mode.
        value: The `execution_params` payload from a Nexus `TradeCommand`.

    Returns:
        The validated per-mode params object.

    Raises:
        TypeError: If the payload shape does not match the mode.
        ValueError: If a key is unsupported or a value is rejected.
    '''

    if mode is ExecutionMode.SINGLE_SHOT:
        return build_single_shot_params(value)

    cls = PARAMS_FOR_MODE.get(mode)

    if cls is None:
        msg = f'no execution_params builder for mode {mode.value}'
        raise ValueError(msg)

    return _build_from_mapping(
        cls, value, mode.name, _FIELD_NAMES[cls], _TUPLE_FIELD_NAMES[cls],
    )


def build_modify_params(mode: ExecutionMode, value: object) -> ModifyParams:

    '''Coerce a Nexus `modify_params` payload into the mode's amend type.

    Dispatches on `mode` to the matching `*Modify` dataclass, validating the
    payload's keys and values. A dataclass instance passes through; a
    `Mapping` is built into the dataclass; any other shape fails closed.
    Every amend field is optional, but the dataclass rejects an all-None
    (empty) amend in its `__post_init__`.

    Args:
        mode: The target command's execution mode.
        value: The `modify_params` payload from a Nexus MODIFY action.

    Returns:
        The validated per-mode amend object.

    Raises:
        TypeError: If the payload shape does not match the mode.
        ValueError: If a key is unsupported, a value is rejected, or the
            mode has no amend builder.
    '''

    cls = MODIFY_PARAMS_FOR_MODE.get(mode)

    if cls is None:
        msg = f'no modify_params builder for mode {mode.value}'
        raise ValueError(msg)

    return _build_from_mapping(
        cls, value, mode.name, _FIELD_NAMES[cls], _TUPLE_FIELD_NAMES[cls],
        payload_label='modify_params',
    )
