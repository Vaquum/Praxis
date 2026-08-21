'''
Tests for the per-mode execution parameter dataclasses, the mode registry,
and TradeCommand's per-mode params validation.
'''

from __future__ import annotations

from datetime import datetime, UTC
from decimal import Decimal

import pytest

from praxis.core.domain.bracket_params import BracketParams
from praxis.core.domain.enums import (
    ExecutionMode,
    MakerPreference,
    OrderSide,
    OrderType,
    STPMode,
)
from praxis.core.domain.execution_params import PARAMS_FOR_MODE
from praxis.core.domain.iceberg_params import IcebergParams
from praxis.core.domain.ladder_dca_params import LadderDcaParams
from praxis.core.domain.scheduled_vwap_params import ScheduledVwapParams
from praxis.core.domain.single_shot_params import SingleShotParams
from praxis.core.domain.time_dca_params import TimeDcaParams
from praxis.core.domain.trade_command import TradeCommand
from praxis.core.domain.twap_params import TwapParams

_TS = datetime(2026, 1, 1, tzinfo=UTC)


def test_bracket_absolute_and_offset_both_accepted() -> None:
    assert BracketParams(take_profit_price=Decimal('110'), stop_loss_price=Decimal('90'))
    assert BracketParams(
        take_profit_offset_bps=Decimal('50'), stop_loss_offset_bps=Decimal('30'),
    )


def test_bracket_rejects_both_or_neither_forms() -> None:
    with pytest.raises(ValueError, match='take_profit'):
        BracketParams(
            take_profit_price=Decimal('110'),
            take_profit_offset_bps=Decimal('50'),
            stop_loss_price=Decimal('90'),
        )

    with pytest.raises(ValueError, match='stop_loss'):
        BracketParams(take_profit_price=Decimal('110'))


def test_bracket_rejects_non_positive() -> None:
    with pytest.raises(ValueError, match='positive'):
        BracketParams(take_profit_price=Decimal('0'), stop_loss_price=Decimal('90'))


def test_twap_valid_and_bounds() -> None:
    assert TwapParams(num_slices=4, interval_seconds=30)

    with pytest.raises(ValueError, match='num_slices'):
        TwapParams(num_slices=1, interval_seconds=30)

    with pytest.raises(ValueError, match='interval_seconds'):
        TwapParams(num_slices=4, interval_seconds=0)


def test_time_dca_valid_and_bounds() -> None:
    assert TimeDcaParams(num_iterations=6, interval_seconds=3600)

    with pytest.raises(ValueError, match='num_iterations'):
        TimeDcaParams(num_iterations=1, interval_seconds=3600)


def test_scheduled_vwap_valid_and_weight_sum() -> None:
    assert ScheduledVwapParams(
        interval_seconds=60,
        volume_weights=(Decimal('0.2'), Decimal('0.3'), Decimal('0.5')),
    )

    with pytest.raises(ValueError, match='sum to 1'):
        ScheduledVwapParams(
            interval_seconds=60, volume_weights=(Decimal('0.2'), Decimal('0.3')),
        )

    with pytest.raises(ValueError, match='at least 2'):
        ScheduledVwapParams(interval_seconds=60, volume_weights=(Decimal('1'),))

    with pytest.raises(ValueError, match='positive'):
        ScheduledVwapParams(
            interval_seconds=60, volume_weights=(Decimal('1.5'), Decimal('-0.5')),
        )


def test_iceberg_valid_and_positive() -> None:
    assert IcebergParams(display_qty=Decimal('0.1'), limit_price=Decimal('50000'))

    with pytest.raises(ValueError, match='positive'):
        IcebergParams(display_qty=Decimal('0'), limit_price=Decimal('50000'))


def test_ladder_dca_monotonic_and_weights() -> None:
    assert LadderDcaParams(price_levels=(Decimal('90'), Decimal('80'), Decimal('70')))
    assert LadderDcaParams(price_levels=(Decimal('70'), Decimal('80'), Decimal('90')))

    with pytest.raises(ValueError, match='monotonic'):
        LadderDcaParams(price_levels=(Decimal('80'), Decimal('80')))

    with pytest.raises(ValueError, match='match price_levels'):
        LadderDcaParams(
            price_levels=(Decimal('90'), Decimal('80')),
            level_weights=(Decimal('1'),),
        )

    with pytest.raises(ValueError, match='sum to 1'):
        LadderDcaParams(
            price_levels=(Decimal('90'), Decimal('80')),
            level_weights=(Decimal('0.4'), Decimal('0.4')),
        )


def test_params_reject_non_finite_decimals() -> None:
    with pytest.raises(ValueError, match='finite'):
        IcebergParams(display_qty=Decimal('Infinity'), limit_price=Decimal('50000'))

    with pytest.raises(ValueError, match='finite'):
        BracketParams(take_profit_price=Decimal('NaN'), stop_loss_price=Decimal('90'))

    with pytest.raises(ValueError, match='finite'):
        LadderDcaParams(price_levels=(Decimal('Infinity'), Decimal('80')))

    with pytest.raises(ValueError, match='finite'):
        ScheduledVwapParams(
            interval_seconds=60, volume_weights=(Decimal('Infinity'), Decimal('0.5')),
        )


def test_params_registry_covers_every_mode() -> None:
    assert set(PARAMS_FOR_MODE) == set(ExecutionMode)
    assert PARAMS_FOR_MODE[ExecutionMode.SINGLE_SHOT] is SingleShotParams
    assert PARAMS_FOR_MODE[ExecutionMode.TWAP] is TwapParams
    assert PARAMS_FOR_MODE[ExecutionMode.BRACKET] is BracketParams


def _command(mode: ExecutionMode, params: object, order_type: OrderType) -> TradeCommand:
    return TradeCommand(
        command_id='cmd-1',
        trade_id='trade-1',
        account_id='acc-1',
        symbol='BTCUSDT',
        side=OrderSide.BUY,
        qty=Decimal('1'),
        order_type=order_type,
        execution_mode=mode,
        execution_params=params,  # type: ignore[arg-type]
        timeout=60,
        reference_price=None,
        maker_preference=MakerPreference.NO_PREFERENCE,
        stp_mode=STPMode.NONE,
        created_at=_TS,
    )


def test_trade_command_accepts_matching_params() -> None:
    assert _command(ExecutionMode.TWAP, TwapParams(num_slices=4, interval_seconds=30), OrderType.MARKET)


def test_trade_command_rejects_mismatched_params() -> None:
    with pytest.raises(TypeError, match='TwapParams'):
        _command(ExecutionMode.TWAP, SingleShotParams(), OrderType.MARKET)


def test_twap_params_reject_bool_fields() -> None:
    with pytest.raises(ValueError, match='interval_seconds'):
        TwapParams(num_slices=4, interval_seconds=True)

    with pytest.raises(ValueError, match='num_slices'):
        TwapParams(num_slices=True, interval_seconds=30)


def test_time_dca_params_reject_bool_fields() -> None:
    with pytest.raises(ValueError, match='interval_seconds'):
        TimeDcaParams(num_iterations=4, interval_seconds=True)

    with pytest.raises(ValueError, match='num_iterations'):
        TimeDcaParams(num_iterations=True, interval_seconds=30)


def test_scheduled_vwap_params_reject_bool_interval() -> None:
    with pytest.raises(ValueError, match='interval_seconds'):
        ScheduledVwapParams(
            interval_seconds=True,
            volume_weights=(Decimal('0.2'), Decimal('0.3'), Decimal('0.5')),
        )
