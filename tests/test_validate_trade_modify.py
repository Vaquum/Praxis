'''
Tests for validate_trade_modify inbound validation (WP-Praxis-0009).
'''

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest

from praxis.core.domain.enums import (
    ExecutionMode,
    MakerPreference,
    OrderSide,
    OrderType,
    STPMode,
)
from praxis.core.domain.iceberg_modify import IcebergModify
from praxis.core.domain.iceberg_params import IcebergParams
from praxis.core.domain.ladder_dca_modify import LadderDcaModify
from praxis.core.domain.ladder_dca_params import LadderDcaParams
from praxis.core.domain.single_shot_modify import SingleShotModify
from praxis.core.domain.single_shot_params import SingleShotParams
from praxis.core.domain.trade_command import TradeCommand
from praxis.core.domain.trade_modify import TradeModify
from praxis.core.domain.twap_modify import TwapModify
from praxis.core.validate_trade_modify import validate_trade_modify

_TS = datetime(2099, 1, 1, tzinfo=UTC)
_ACCT = 'acc-1'
_CMD = '11111111-2222-3333-4444-555555555555'


def _iceberg_command(side: OrderSide = OrderSide.BUY) -> TradeCommand:
    return TradeCommand(
        command_id=_CMD,
        trade_id='trade-1',
        account_id=_ACCT,
        symbol='BTCUSDT',
        side=side,
        qty=Decimal('1'),
        order_type=OrderType.LIMIT,
        execution_mode=ExecutionMode.ICEBERG,
        execution_params=IcebergParams(
            display_qty=Decimal('0.1'), limit_price=Decimal('50000'),
        ),
        timeout=3600,
        reference_price=None,
        maker_preference=MakerPreference.NO_PREFERENCE,
        stp_mode=STPMode.NONE,
        created_at=_TS,
    )


def _modify(**overrides: object) -> TradeModify:
    kwargs: dict[str, object] = {
        'command_id': _CMD,
        'account_id': _ACCT,
        'reason': 'reprice',
        'modify_params': IcebergModify(limit_price=Decimal('49000')),
        'created_at': _TS,
    }
    kwargs.update(overrides)
    return TradeModify(**kwargs)  # type: ignore[arg-type]


class TestValidateTradeModify:

    def test_valid_modify_enqueues(self) -> None:
        commands = {_CMD: _iceberg_command()}

        assert validate_trade_modify(_modify(), commands, set()) is True

    def test_unknown_command_rejected(self) -> None:
        with pytest.raises(ValueError, match='unknown command_id'):
            validate_trade_modify(_modify(), {}, set())

    def test_account_mismatch_rejected(self) -> None:
        commands = {_CMD: _iceberg_command()}

        with pytest.raises(ValueError, match='account_id mismatch'):
            validate_trade_modify(_modify(account_id='other'), commands, set())

    def test_mode_mismatch_rejected(self) -> None:
        commands = {_CMD: _iceberg_command()}

        with pytest.raises(ValueError, match='does not match execution mode'):
            validate_trade_modify(
                _modify(modify_params=TwapModify(interval_seconds=30)),
                commands,
                set(),
            )

    def test_terminal_command_is_noop(self) -> None:
        commands = {_CMD: _iceberg_command()}

        assert validate_trade_modify(_modify(), commands, {_CMD}) is False


def _single_shot_command(side: OrderSide = OrderSide.BUY) -> TradeCommand:
    return TradeCommand(
        command_id=_CMD,
        trade_id='trade-1',
        account_id=_ACCT,
        symbol='BTCUSDT',
        side=side,
        qty=Decimal('1'),
        order_type=OrderType.LIMIT,
        execution_mode=ExecutionMode.SINGLE_SHOT,
        execution_params=SingleShotParams(price=Decimal('50000')),
        timeout=3600,
        reference_price=None,
        maker_preference=MakerPreference.NO_PREFERENCE,
        stp_mode=STPMode.NONE,
        created_at=_TS,
    )


def _ladder_command() -> TradeCommand:
    return TradeCommand(
        command_id=_CMD,
        trade_id='trade-1',
        account_id=_ACCT,
        symbol='BTCUSDT',
        side=OrderSide.BUY,
        qty=Decimal('1'),
        order_type=OrderType.LIMIT,
        execution_mode=ExecutionMode.LADDER_DCA,
        execution_params=LadderDcaParams(
            price_levels=(Decimal('49000'), Decimal('48000')),
        ),
        timeout=3600,
        reference_price=None,
        maker_preference=MakerPreference.NO_PREFERENCE,
        stp_mode=STPMode.NONE,
        created_at=_TS,
    )


class TestExposureCeiling:

    def test_buy_price_decrease_allowed(self) -> None:
        commands = {_CMD: _iceberg_command()}

        assert validate_trade_modify(
            _modify(modify_params=IcebergModify(limit_price=Decimal('49000'))),
            commands,
            set(),
        ) is True

    def test_buy_price_increase_rejected(self) -> None:
        commands = {_CMD: _iceberg_command()}

        with pytest.raises(ValueError, match='raises buy-side quote exposure'):
            validate_trade_modify(
                _modify(modify_params=IcebergModify(limit_price=Decimal('51000'))),
                commands,
                set(),
            )

    def test_buy_non_price_amend_allowed(self) -> None:
        commands = {_CMD: _iceberg_command()}

        assert validate_trade_modify(
            _modify(modify_params=IcebergModify(display_qty=Decimal('0.2'))),
            commands,
            set(),
        ) is True

    def test_sell_price_increase_allowed(self) -> None:
        commands = {_CMD: _iceberg_command(side=OrderSide.SELL)}

        assert validate_trade_modify(
            _modify(modify_params=IcebergModify(limit_price=Decimal('51000'))),
            commands,
            set(),
        ) is True

    def test_single_shot_buy_price_increase_rejected(self) -> None:
        commands = {_CMD: _single_shot_command()}

        with pytest.raises(ValueError, match='raises buy-side quote exposure'):
            validate_trade_modify(
                _modify(modify_params=SingleShotModify(price=Decimal('51000'))),
                commands,
                set(),
            )

    def test_stop_trigger_amend_not_ceilinged(self) -> None:
        commands = {_CMD: _single_shot_command()}

        assert validate_trade_modify(
            _modify(modify_params=SingleShotModify(stop_price=Decimal('60000'))),
            commands,
            set(),
        ) is True

    def test_ladder_buy_one_level_up_rejected(self) -> None:
        commands = {_CMD: _ladder_command()}

        with pytest.raises(ValueError, match='raises buy-side quote exposure'):
            validate_trade_modify(
                _modify(
                    modify_params=LadderDcaModify(
                        price_levels=(Decimal('49500'), Decimal('48000')),
                    ),
                ),
                commands,
                set(),
            )

    def test_ladder_buy_all_levels_down_allowed(self) -> None:
        commands = {_CMD: _ladder_command()}

        assert validate_trade_modify(
            _modify(
                modify_params=LadderDcaModify(
                    price_levels=(Decimal('48500'), Decimal('47500')),
                ),
            ),
            commands,
            set(),
        ) is True

    def test_ladder_buy_different_rung_count_rejected(self) -> None:
        commands = {_CMD: _ladder_command()}

        with pytest.raises(ValueError, match='raises buy-side quote exposure'):
            validate_trade_modify(
                _modify(
                    modify_params=LadderDcaModify(
                        price_levels=(
                            Decimal('49000'), Decimal('48000'), Decimal('47000'),
                        ),
                    ),
                ),
                commands,
                set(),
            )
