'''
Tests for TradeCommand, TradeAbort, SingleShotParams, and new enums.
'''

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

import pytest

from praxis.core.domain import (
    ExecutionMode,
    MakerPreference,
    OrderSide,
    OrderType,
    STPMode,
    SingleShotParams,
    TradeAbort,
    TradeCommand,
)

_TS = datetime(2026, 1, 1, tzinfo=timezone.utc)


def _command(
    qty: Decimal = Decimal('1.0'),
    timeout: int = 60,
    reference_price: Decimal | None = None,
    execution_params: SingleShotParams | None = None,
) -> TradeCommand:
    return TradeCommand(
        command_id='cmd-001',
        trade_id='trade-001',
        account_id='acc-1',
        symbol='BTCUSDT',
        side=OrderSide.BUY,
        qty=qty,
        order_type=OrderType.LIMIT,
        execution_mode=ExecutionMode.SINGLE_SHOT,
        execution_params=execution_params or SingleShotParams(price=Decimal('50000.00')),
        timeout=timeout,
        reference_price=reference_price,
        maker_preference=MakerPreference.NO_PREFERENCE,
        stp_mode=STPMode.NONE,
        created_at=_TS,
    )


def _abort() -> TradeAbort:
    return TradeAbort(
        command_id='cmd-001',
        account_id='acc-1',
        reason='operator_cancel',
        created_at=_TS,
    )


def test_execution_mode_members() -> None:
    expected = {
        ExecutionMode.SINGLE_SHOT,
        ExecutionMode.BRACKET,
        ExecutionMode.TWAP,
        ExecutionMode.SCHEDULED_VWAP,
        ExecutionMode.ICEBERG,
        ExecutionMode.TIME_DCA,
        ExecutionMode.LADDER_DCA,
    }
    assert set(ExecutionMode) == expected


def test_maker_preference_members() -> None:
    expected = {
        MakerPreference.MAKER_ONLY,
        MakerPreference.MAKER_PREFERRED,
        MakerPreference.NO_PREFERENCE,
    }
    assert set(MakerPreference) == expected


def test_stp_mode_members() -> None:
    expected = {
        STPMode.EXPIRE_TAKER,
        STPMode.EXPIRE_MAKER,
        STPMode.EXPIRE_BOTH,
        STPMode.NONE,
    }
    assert set(STPMode) == expected


def test_enum_values_are_strings() -> None:
    for enum_cls in (ExecutionMode, MakerPreference, STPMode):
        for member in enum_cls:
            assert isinstance(member.value, str)


def test_single_shot_params_creation() -> None:
    params = SingleShotParams(price=Decimal('50000.00'))
    assert params.price == Decimal('50000.00')
    assert params.stop_price is None
    assert params.stop_limit_price is None


def test_single_shot_params_all_fields() -> None:
    params = SingleShotParams(
        price=Decimal('50000.00'),
        stop_price=Decimal('49000.00'),
        stop_limit_price=Decimal('48500.00'),
    )
    assert params.stop_price == Decimal('49000.00')
    assert params.stop_limit_price == Decimal('48500.00')


def test_single_shot_params_frozen() -> None:
    params = SingleShotParams(price=Decimal('50000.00'))
    with pytest.raises(AttributeError):
        params.price = Decimal('999')  # type: ignore[misc]


@pytest.mark.parametrize('bad', [Decimal('0'), Decimal('-1')])
def test_single_shot_params_rejects_non_positive_price(bad: Decimal) -> None:
    with pytest.raises(ValueError, match='positive'):
        SingleShotParams(price=bad)


@pytest.mark.parametrize('bad', [Decimal('0'), Decimal('-1')])
def test_single_shot_params_rejects_non_positive_stop_price(bad: Decimal) -> None:
    with pytest.raises(ValueError, match='positive'):
        SingleShotParams(stop_price=bad)


@pytest.mark.parametrize('bad', [Decimal('0'), Decimal('-1')])
def test_single_shot_params_rejects_non_positive_stop_limit_price(bad: Decimal) -> None:
    with pytest.raises(ValueError, match='positive'):
        SingleShotParams(stop_limit_price=bad)


def test_single_shot_params_none_prices_valid() -> None:
    params = SingleShotParams()
    assert params.price is None
    assert params.stop_price is None
    assert params.stop_limit_price is None


def test_trade_command_creation() -> None:
    cmd = _command()
    assert cmd.command_id == 'cmd-001'
    assert cmd.symbol == 'BTCUSDT'
    assert cmd.execution_mode == ExecutionMode.SINGLE_SHOT
    assert cmd.maker_preference == MakerPreference.NO_PREFERENCE
    assert cmd.stp_mode == STPMode.NONE


def test_trade_command_frozen() -> None:
    cmd = _command()
    with pytest.raises(AttributeError):
        cmd.qty = Decimal('999')  # type: ignore[misc]


@pytest.mark.parametrize('bad', [Decimal('0'), Decimal('-1')])
def test_trade_command_rejects_non_positive_qty(bad: Decimal) -> None:
    with pytest.raises(ValueError, match='positive'):
        _command(qty=bad)


@pytest.mark.parametrize('bad', [0, -1])
def test_trade_command_rejects_non_positive_timeout(bad: int) -> None:
    with pytest.raises(ValueError, match='positive'):
        _command(timeout=bad)


@pytest.mark.parametrize('bad', [Decimal('0'), Decimal('-1')])
def test_trade_command_rejects_non_positive_reference_price(bad: Decimal) -> None:
    with pytest.raises(ValueError, match='positive'):
        _command(reference_price=bad)


def test_trade_command_none_reference_price_valid() -> None:
    cmd = _command(reference_price=None)
    assert cmd.reference_price is None


def test_trade_command_rejects_naive_created_at() -> None:
    with pytest.raises(ValueError, match='timezone-aware'):
        TradeCommand(
            command_id='cmd-001',
            trade_id='trade-001',
            account_id='acc-1',
            symbol='BTCUSDT',
            side=OrderSide.BUY,
            qty=Decimal('1.0'),
            order_type=OrderType.LIMIT,
            execution_mode=ExecutionMode.SINGLE_SHOT,
            execution_params=SingleShotParams(price=Decimal('50000.00')),
            timeout=60,
            reference_price=None,
            maker_preference=MakerPreference.NO_PREFERENCE,
            stp_mode=STPMode.NONE,
            created_at=datetime(2026, 1, 1),
        )


def test_trade_command_financial_values_are_decimal() -> None:
    cmd = _command(reference_price=Decimal('49000.00'))
    assert isinstance(cmd.qty, Decimal)
    assert isinstance(cmd.reference_price, Decimal)


def test_trade_abort_creation() -> None:
    abort = _abort()
    assert abort.command_id == 'cmd-001'
    assert abort.account_id == 'acc-1'
    assert abort.reason == 'operator_cancel'


def test_trade_abort_frozen() -> None:
    abort = _abort()
    with pytest.raises(AttributeError):
        abort.reason = 'changed'  # type: ignore[misc]


def test_trade_abort_rejects_naive_created_at() -> None:
    with pytest.raises(ValueError, match='timezone-aware'):
        TradeAbort(
            command_id='cmd-001',
            account_id='acc-1',
            reason='test',
            created_at=datetime(2026, 1, 1),
        )
