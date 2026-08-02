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

`build_execution_params` extends this to every execution mode: it dispatches
on the mode to the matching per-mode params dataclass (`SingleShotParams`,
`TwapParams`, `BracketParams`, and the rest), rejecting keys outside the
mode's field set and coercing list payloads to the tuples the dataclasses
expect. SINGLE_SHOT keeps `build_single_shot_params` — it alone accepts an
omitted (`None`) payload and type-checks Decimals directly; the other modes
self-validate in their dataclass `__post_init__`.
'''

from __future__ import annotations

from collections.abc import Mapping
from decimal import Decimal
from enum import Enum
from typing import Any

from praxis.core.domain.bracket_params import BracketParams
from praxis.core.domain.enums import (
    ExecutionMode,
    MakerPreference,
    OrderSide,
    OrderType,
    STPMode,
)
from praxis.core.domain.execution_params import ExecutionParams
from praxis.core.domain.iceberg_params import IcebergParams
from praxis.core.domain.ladder_dca_params import LadderDcaParams
from praxis.core.domain.scheduled_vwap_params import ScheduledVwapParams
from praxis.core.domain.single_shot_params import SingleShotParams
from praxis.core.domain.time_dca_params import TimeDcaParams
from praxis.core.domain.twap_params import TwapParams

__all__ = [
    'build_execution_params',
    'build_single_shot_params',
    'translate_execution_mode',
    'translate_maker_preference',
    'translate_order_side',
    'translate_order_type',
    'translate_stp_mode',
]

_BRACKET_KEYS = frozenset({
    'take_profit_price',
    'take_profit_offset_bps',
    'stop_loss_price',
    'stop_loss_offset_bps',
    'stop_loss_limit_price',
})
_TWAP_KEYS = frozenset({'num_slices', 'interval_seconds'})
_TIME_DCA_KEYS = frozenset({'num_iterations', 'interval_seconds'})
_SCHEDULED_VWAP_KEYS = frozenset({'interval_seconds', 'volume_weights'})
_ICEBERG_KEYS = frozenset({'display_qty', 'limit_price'})
_LADDER_DCA_KEYS = frozenset({'price_levels', 'level_weights'})

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


def _build_from_mapping[P](
    cls: type[P],
    value: object,
    mode_label: str,
    allowed_keys: frozenset[str],
    tuple_keys: frozenset[str] = frozenset(),
) -> P:

    '''Build a per-mode params dataclass from a Nexus `execution_params` mapping.

    Args:
        cls: The target params dataclass.
        value: The `execution_params` payload — a `cls` instance (passed
            through) or a `Mapping` of its field names.
        mode_label: Execution-mode name for error messages.
        allowed_keys: Field names accepted for this mode.
        tuple_keys: Field names whose list payloads are coerced to tuples.

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
            f'execution_params for {mode_label} must be {cls.__name__} or a '
            f'Mapping, got {type(value).__name__}'
        )
        raise TypeError(msg)

    unknown = set(value.keys()) - allowed_keys
    if unknown:
        msg = (
            f'execution_params has unsupported keys for {mode_label}: '
            f'{sorted(unknown)} (allowed: {sorted(allowed_keys)})'
        )
        raise ValueError(msg)

    kwargs: dict[str, Any] = {}
    for key, raw in value.items():
        kwargs[key] = tuple(raw) if key in tuple_keys and isinstance(raw, list) else raw

    return cls(**kwargs)


def build_execution_params(  # noqa: PLR0911 - one return per execution mode
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

    if mode is ExecutionMode.BRACKET:
        return _build_from_mapping(BracketParams, value, 'BRACKET', _BRACKET_KEYS)

    if mode is ExecutionMode.TWAP:
        return _build_from_mapping(TwapParams, value, 'TWAP', _TWAP_KEYS)

    if mode is ExecutionMode.TIME_DCA:
        return _build_from_mapping(TimeDcaParams, value, 'TIME_DCA', _TIME_DCA_KEYS)

    if mode is ExecutionMode.SCHEDULED_VWAP:
        return _build_from_mapping(
            ScheduledVwapParams, value, 'SCHEDULED_VWAP', _SCHEDULED_VWAP_KEYS,
            frozenset({'volume_weights'}),
        )

    if mode is ExecutionMode.ICEBERG:
        return _build_from_mapping(IcebergParams, value, 'ICEBERG', _ICEBERG_KEYS)

    if mode is ExecutionMode.LADDER_DCA:
        return _build_from_mapping(
            LadderDcaParams, value, 'LADDER_DCA', _LADDER_DCA_KEYS,
            frozenset({'price_levels', 'level_weights'}),
        )

    msg = f'no execution_params builder for mode {mode.value}'
    raise ValueError(msg)
