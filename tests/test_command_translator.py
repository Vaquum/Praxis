'''Tests for `build_single_shot_params` (PT-FIX-7) and the
`translate_*` enum helpers that re-key Nexus enums to the Praxis
equivalents at the launcher's `submit_command` boundary.

Pre-fix (PT-FIX-7): `PraxisOutbound.send_command` forwarded
`Action.execution_params: Mapping[str, object] | None` straight into
`Trading.submit_command`. The Praxis `TradeCommand.__post_init__`
enforces `isinstance(execution_params, SingleShotParams)` for
SINGLE_SHOT mode and raised `TypeError` on every order.

Pre-fix (enum translation): the launcher's
`submit_command_with_translated_params` forwarded `side`, `order_type`,
`execution_mode`, `maker_preference`, and `stp_mode` straight from
the Nexus `TradeCommand` into Praxis. Even though the value strings
agree (except `STPMode`), the Nexus and Praxis enum classes are
distinct objects, so any Praxis-side dict lookup keyed by the enum
(`_ALLOWED_ORDER_TYPES.get(cmd.execution_mode)`) returned `None` and
`validate_trade_command` rejected every command with `no allowed
order types configured for mode SINGLE_SHOT`.

Post-fix: the launcher routes each enum kwarg through the matching
`translate_*` helper before reaching `Trading.submit_command`, so
the Praxis validator and dataclass invariants see Praxis enum
members.
'''

from __future__ import annotations

from decimal import Decimal
from enum import Enum

import pytest

from praxis.command_translator import (
    build_single_shot_params,
    translate_execution_mode,
    translate_maker_preference,
    translate_order_side,
    translate_order_type,
    translate_stp_mode,
)
from praxis.core.domain.enums import (
    ExecutionMode,
    MakerPreference,
    OrderSide,
    OrderType,
    STPMode,
)
from praxis.core.domain.single_shot_params import SingleShotParams


def test_none_returns_default_single_shot_params() -> None:

    result = build_single_shot_params(None)

    assert isinstance(result, SingleShotParams)
    assert result.price is None
    assert result.stop_price is None
    assert result.stop_limit_price is None


def test_empty_mapping_returns_default_single_shot_params() -> None:

    result = build_single_shot_params({})

    assert isinstance(result, SingleShotParams)
    assert result.price is None
    assert result.stop_price is None
    assert result.stop_limit_price is None


def test_mapping_with_price_only_is_translated() -> None:

    result = build_single_shot_params({'price': Decimal('100.50')})

    assert result.price == Decimal('100.50')
    assert result.stop_price is None
    assert result.stop_limit_price is None


def test_mapping_with_all_fields_is_translated() -> None:

    payload = {
        'price': Decimal('100'),
        'stop_price': Decimal('95'),
        'stop_limit_price': Decimal('94'),
    }

    result = build_single_shot_params(payload)

    assert result.price == Decimal('100')
    assert result.stop_price == Decimal('95')
    assert result.stop_limit_price == Decimal('94')


def test_pre_built_single_shot_params_passes_through_unchanged() -> None:

    sentinel = SingleShotParams(price=Decimal('50'))

    result = build_single_shot_params(sentinel)

    assert result is sentinel


def test_unknown_key_raises_value_error() -> None:

    with pytest.raises(ValueError, match='unsupported keys'):
        build_single_shot_params({'price': Decimal('100'), 'iceberg_qty': Decimal('5')})


def test_non_decimal_value_raises_type_error() -> None:

    with pytest.raises(TypeError, match='must be Decimal or None'):
        build_single_shot_params({'price': 100.5})


def test_non_mapping_non_params_value_raises_type_error() -> None:

    with pytest.raises(TypeError, match='None, Mapping, or SingleShotParams'):
        build_single_shot_params('limit')  # type: ignore[arg-type]


def test_negative_price_propagates_value_error_from_dataclass() -> None:

    with pytest.raises(ValueError, match='price must be positive'):
        build_single_shot_params({'price': Decimal('-1')})


def test_explicit_none_in_mapping_treated_as_unset() -> None:

    result = build_single_shot_params(
        {
            'price': Decimal('100'),
            'stop_price': None,
            'stop_limit_price': None,
        },
    )

    assert result.price == Decimal('100')
    assert result.stop_price is None
    assert result.stop_limit_price is None


class _NexusOrderSide(Enum):

    BUY = 'BUY'
    SELL = 'SELL'


class _NexusOrderType(Enum):

    MARKET = 'MARKET'
    LIMIT = 'LIMIT'


class _NexusExecutionMode(Enum):

    SINGLE_SHOT = 'SINGLE_SHOT'


class _NexusMakerPreference(Enum):

    NO_PREFERENCE = 'NO_PREFERENCE'
    MAKER_ONLY = 'MAKER_ONLY'


class _NexusSTPMode(Enum):

    CANCEL_MAKER = 'CANCEL_MAKER'
    CANCEL_TAKER = 'CANCEL_TAKER'
    CANCEL_BOTH = 'CANCEL_BOTH'


def test_translate_order_side_passes_praxis_member_through() -> None:

    assert translate_order_side(OrderSide.BUY) is OrderSide.BUY


def test_translate_order_side_rekeys_foreign_enum_to_praxis() -> None:

    result = translate_order_side(_NexusOrderSide.BUY)

    assert result is OrderSide.BUY
    assert type(result) is OrderSide


def test_translate_order_side_rejects_non_enum_value() -> None:

    with pytest.raises(TypeError, match='side must be a OrderSide'):
        translate_order_side('BUY')


def test_translate_order_type_rekeys_foreign_enum_to_praxis() -> None:

    result = translate_order_type(_NexusOrderType.MARKET)

    assert result is OrderType.MARKET
    assert type(result) is OrderType


def test_translate_order_type_passes_praxis_member_through() -> None:

    assert translate_order_type(OrderType.LIMIT) is OrderType.LIMIT


def test_translate_execution_mode_rekeys_foreign_enum_to_praxis() -> None:

    result = translate_execution_mode(_NexusExecutionMode.SINGLE_SHOT)

    assert result is ExecutionMode.SINGLE_SHOT
    assert type(result) is ExecutionMode


def test_translate_execution_mode_passes_praxis_member_through() -> None:

    assert translate_execution_mode(ExecutionMode.SINGLE_SHOT) is ExecutionMode.SINGLE_SHOT


def test_translate_maker_preference_rekeys_foreign_enum_to_praxis() -> None:

    result = translate_maker_preference(_NexusMakerPreference.MAKER_ONLY)

    assert result is MakerPreference.MAKER_ONLY
    assert type(result) is MakerPreference


def test_translate_maker_preference_passes_praxis_member_through() -> None:

    assert translate_maker_preference(MakerPreference.NO_PREFERENCE) is MakerPreference.NO_PREFERENCE


def test_translate_stp_mode_maps_nexus_cancel_taker_to_praxis_expire_taker() -> None:

    result = translate_stp_mode(_NexusSTPMode.CANCEL_TAKER)

    assert result is STPMode.EXPIRE_TAKER
    assert type(result) is STPMode


def test_translate_stp_mode_maps_nexus_cancel_maker_to_praxis_expire_maker() -> None:

    assert translate_stp_mode(_NexusSTPMode.CANCEL_MAKER) is STPMode.EXPIRE_MAKER


def test_translate_stp_mode_maps_nexus_cancel_both_to_praxis_expire_both() -> None:

    assert translate_stp_mode(_NexusSTPMode.CANCEL_BOTH) is STPMode.EXPIRE_BOTH


def test_translate_stp_mode_passes_praxis_member_through() -> None:

    assert translate_stp_mode(STPMode.NONE) is STPMode.NONE


def test_translate_rejects_unknown_value() -> None:

    class _Foreign(Enum):

        FROBNICATE = 'FROBNICATE'

    with pytest.raises(ValueError, match='execution_mode value'):
        translate_execution_mode(_Foreign.FROBNICATE)


def test_translate_rejects_none() -> None:

    with pytest.raises(TypeError, match='must be a OrderSide'):
        translate_order_side(None)
