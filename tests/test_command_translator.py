'''Tests for `build_single_shot_params` (PT-FIX-7).

Pre-fix: `PraxisOutbound.send_command` forwarded
`Action.execution_params: Mapping[str, object] | None` straight into
`Trading.submit_command`. The Praxis `TradeCommand.__post_init__`
enforces `isinstance(execution_params, SingleShotParams)` for
SINGLE_SHOT mode and raised `TypeError` on every order.

Post-fix: the launcher wraps `submit_fn` with
`build_single_shot_params(...)` so all three Nexus shapes (`None`,
`Mapping`, pre-built `SingleShotParams`) resolve to a valid
`SingleShotParams` before reaching `Trading.submit_command`.
'''

from __future__ import annotations

from decimal import Decimal

import pytest

from praxis.command_translator import build_single_shot_params
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
