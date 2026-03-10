'''
Tests for praxis.core.validate_trade_command.
'''

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

import pytest

from praxis.core.domain.enums import (
    ExecutionMode,
    MakerPreference,
    OrderSide,
    OrderType,
    STPMode,
)
from praxis.core.domain.single_shot_params import SingleShotParams
from praxis.core.domain.trade_command import TradeCommand
from praxis.core.validate_trade_command import validate_trade_command
from praxis.infrastructure.venue_adapter import SymbolFilters

_NOW = datetime.now(timezone.utc)


def _cmd(
    *,
    order_type: OrderType = OrderType.MARKET,
    execution_mode: ExecutionMode = ExecutionMode.SINGLE_SHOT,
    execution_params: SingleShotParams | None = None,
    maker_preference: MakerPreference = MakerPreference.NO_PREFERENCE,
    qty: Decimal = Decimal('0.01'),
    reference_price: Decimal | None = None,
) -> TradeCommand:
    if execution_params is None:
        execution_params = SingleShotParams()

    return TradeCommand(
        command_id='cmd-001',
        trade_id='trade-001',
        account_id='acct-001',
        symbol='BTCUSDT',
        side=OrderSide.BUY,
        qty=qty,
        order_type=order_type,
        execution_mode=execution_mode,
        execution_params=execution_params,
        timeout=60,
        reference_price=reference_price,
        maker_preference=maker_preference,
        stp_mode=STPMode.NONE,
        created_at=_NOW,
    )


_FILTERS = SymbolFilters(
    symbol='BTCUSDT',
    tick_size=Decimal('0.01'),
    lot_step=Decimal('0.001'),
    lot_min=Decimal('0.001'),
    lot_max=Decimal('100'),
    min_notional=Decimal('10'),
)


class TestModeOrderTypeAllowed:
    @pytest.mark.parametrize(
        'ot',
        [
            OrderType.MARKET,
            OrderType.LIMIT,
            OrderType.LIMIT_IOC,
            OrderType.STOP,
            OrderType.STOP_LIMIT,
            OrderType.TAKE_PROFIT,
            OrderType.TP_LIMIT,
            OrderType.OCO,
        ],
    )
    def test_single_shot_accepts_all_order_types(self, ot: OrderType) -> None:
        params = SingleShotParams()
        if ot in {OrderType.LIMIT, OrderType.LIMIT_IOC}:
            params = SingleShotParams(price=Decimal('50000'))
        elif ot == OrderType.STOP:
            params = SingleShotParams(stop_price=Decimal('49000'))
        elif ot == OrderType.STOP_LIMIT:
            params = SingleShotParams(
                price=Decimal('50000'), stop_price=Decimal('49000')
            )
        elif ot == OrderType.TAKE_PROFIT:
            params = SingleShotParams(stop_price=Decimal('51000'))
        elif ot == OrderType.TP_LIMIT:
            params = SingleShotParams(
                price=Decimal('51000'), stop_price=Decimal('51000')
            )
        elif ot == OrderType.OCO:
            params = SingleShotParams(
                price=Decimal('50000'),
                stop_price=Decimal('49000'),
                stop_limit_price=Decimal('48500'),
            )
        validate_trade_command(_cmd(order_type=ot, execution_params=params))

    @pytest.mark.parametrize(
        'ot',
        [
            OrderType.MARKET,
            OrderType.LIMIT,
            OrderType.LIMIT_IOC,
            OrderType.STOP,
            OrderType.STOP_LIMIT,
        ],
    )
    def test_bracket_accepts_allowed_types(self, ot: OrderType) -> None:
        params = SingleShotParams()
        if ot in {OrderType.LIMIT, OrderType.LIMIT_IOC}:
            params = SingleShotParams(price=Decimal('50000'))
        elif ot == OrderType.STOP:
            params = SingleShotParams(stop_price=Decimal('49000'))
        elif ot == OrderType.STOP_LIMIT:
            params = SingleShotParams(
                price=Decimal('50000'), stop_price=Decimal('49000')
            )
        validate_trade_command(
            _cmd(
                order_type=ot,
                execution_mode=ExecutionMode.BRACKET,
                execution_params=params,
            ),
        )

    @pytest.mark.parametrize(
        'ot',
        [
            OrderType.TAKE_PROFIT,
            OrderType.TP_LIMIT,
            OrderType.OCO,
        ],
    )
    def test_bracket_rejects_disallowed_types(self, ot: OrderType) -> None:
        with pytest.raises(ValueError, match='BRACKET does not support'):
            validate_trade_command(
                _cmd(order_type=ot, execution_mode=ExecutionMode.BRACKET),
            )

    @pytest.mark.parametrize(
        'mode',
        [
            ExecutionMode.TWAP,
            ExecutionMode.SCHEDULED_VWAP,
            ExecutionMode.TIME_DCA,
        ],
    )
    @pytest.mark.parametrize(
        'ot',
        [
            OrderType.MARKET,
            OrderType.LIMIT,
            OrderType.LIMIT_IOC,
        ],
    )
    def test_slicing_modes_accept_market_limit_ioc(
        self,
        mode: ExecutionMode,
        ot: OrderType,
    ) -> None:
        validate_trade_command(_cmd(order_type=ot, execution_mode=mode))

    @pytest.mark.parametrize(
        'mode',
        [
            ExecutionMode.TWAP,
            ExecutionMode.SCHEDULED_VWAP,
            ExecutionMode.TIME_DCA,
        ],
    )
    @pytest.mark.parametrize(
        'ot',
        [
            OrderType.STOP,
            OrderType.STOP_LIMIT,
            OrderType.TAKE_PROFIT,
            OrderType.TP_LIMIT,
            OrderType.OCO,
        ],
    )
    def test_slicing_modes_reject_stop_and_composite(
        self,
        mode: ExecutionMode,
        ot: OrderType,
    ) -> None:
        with pytest.raises(ValueError, match='does not support'):
            validate_trade_command(_cmd(order_type=ot, execution_mode=mode))

    def test_iceberg_accepts_limit_only(self) -> None:
        validate_trade_command(
            _cmd(order_type=OrderType.LIMIT, execution_mode=ExecutionMode.ICEBERG),
        )

    @pytest.mark.parametrize(
        'ot',
        [
            OrderType.MARKET,
            OrderType.LIMIT_IOC,
            OrderType.STOP,
            OrderType.STOP_LIMIT,
            OrderType.TAKE_PROFIT,
            OrderType.TP_LIMIT,
            OrderType.OCO,
        ],
    )
    def test_iceberg_rejects_non_limit(self, ot: OrderType) -> None:
        with pytest.raises(ValueError, match='ICEBERG does not support'):
            validate_trade_command(
                _cmd(order_type=ot, execution_mode=ExecutionMode.ICEBERG)
            )

    @pytest.mark.parametrize('ot', [OrderType.LIMIT, OrderType.STOP_LIMIT])
    def test_ladder_dca_accepts_limit_and_stop_limit(self, ot: OrderType) -> None:
        validate_trade_command(
            _cmd(order_type=ot, execution_mode=ExecutionMode.LADDER_DCA),
        )

    @pytest.mark.parametrize(
        'ot',
        [
            OrderType.MARKET,
            OrderType.LIMIT_IOC,
            OrderType.STOP,
            OrderType.TAKE_PROFIT,
            OrderType.TP_LIMIT,
            OrderType.OCO,
        ],
    )
    def test_ladder_dca_rejects_disallowed(self, ot: OrderType) -> None:
        with pytest.raises(ValueError, match='LADDER_DCA does not support'):
            validate_trade_command(
                _cmd(order_type=ot, execution_mode=ExecutionMode.LADDER_DCA),
            )


class TestSingleShotParamsCoherence:
    def test_market_accepts_no_prices(self) -> None:
        validate_trade_command(_cmd(order_type=OrderType.MARKET))

    def test_market_rejects_spurious_price(self) -> None:
        with pytest.raises(
            ValueError, match=r'MARKET does not use execution_params\.price'
        ):
            validate_trade_command(
                _cmd(
                    order_type=OrderType.MARKET,
                    execution_params=SingleShotParams(price=Decimal('50000')),
                ),
            )

    def test_market_rejects_spurious_stop_price(self) -> None:
        with pytest.raises(
            ValueError, match=r'MARKET does not use execution_params\.stop_price'
        ):
            validate_trade_command(
                _cmd(
                    order_type=OrderType.MARKET,
                    execution_params=SingleShotParams(stop_price=Decimal('49000')),
                ),
            )

    def test_limit_requires_price(self) -> None:
        with pytest.raises(ValueError, match=r'LIMIT requires execution_params\.price'):
            validate_trade_command(_cmd(order_type=OrderType.LIMIT))

    def test_limit_accepts_price(self) -> None:
        validate_trade_command(
            _cmd(
                order_type=OrderType.LIMIT,
                execution_params=SingleShotParams(price=Decimal('50000')),
            ),
        )

    def test_stop_requires_stop_price(self) -> None:
        with pytest.raises(
            ValueError, match=r'STOP requires execution_params\.stop_price'
        ):
            validate_trade_command(_cmd(order_type=OrderType.STOP))

    def test_stop_accepts_stop_price(self) -> None:
        validate_trade_command(
            _cmd(
                order_type=OrderType.STOP,
                execution_params=SingleShotParams(stop_price=Decimal('49000')),
            ),
        )

    def test_stop_limit_requires_both(self) -> None:
        with pytest.raises(ValueError, match='STOP_LIMIT requires'):
            validate_trade_command(
                _cmd(
                    order_type=OrderType.STOP_LIMIT,
                    execution_params=SingleShotParams(stop_price=Decimal('49000')),
                ),
            )

    def test_stop_limit_accepts_both(self) -> None:
        validate_trade_command(
            _cmd(
                order_type=OrderType.STOP_LIMIT,
                execution_params=SingleShotParams(
                    price=Decimal('50000'),
                    stop_price=Decimal('49000'),
                ),
            ),
        )

    def test_oco_requires_all_three(self) -> None:
        with pytest.raises(ValueError, match='OCO requires'):
            validate_trade_command(
                _cmd(
                    order_type=OrderType.OCO,
                    execution_params=SingleShotParams(
                        price=Decimal('50000'),
                        stop_price=Decimal('49000'),
                    ),
                ),
            )

    def test_oco_accepts_all_three(self) -> None:
        validate_trade_command(
            _cmd(
                order_type=OrderType.OCO,
                execution_params=SingleShotParams(
                    price=Decimal('50000'),
                    stop_price=Decimal('49000'),
                    stop_limit_price=Decimal('48500'),
                ),
            ),
        )

    def test_limit_rejects_spurious_stop_price(self) -> None:
        with pytest.raises(
            ValueError, match=r'LIMIT does not use execution_params\.stop_price'
        ):
            validate_trade_command(
                _cmd(
                    order_type=OrderType.LIMIT,
                    execution_params=SingleShotParams(
                        price=Decimal('50000'),
                        stop_price=Decimal('49000'),
                    ),
                ),
            )

    def test_limit_rejects_spurious_stop_limit_price(self) -> None:
        with pytest.raises(
            ValueError,
            match=r'LIMIT does not use execution_params\.stop_limit_price',
        ):
            validate_trade_command(
                _cmd(
                    order_type=OrderType.LIMIT,
                    execution_params=SingleShotParams(
                        price=Decimal('50000'),
                        stop_limit_price=Decimal('48500'),
                    ),
                ),
            )


class TestMakerPreference:
    def test_maker_only_accepts_limit(self) -> None:
        validate_trade_command(
            _cmd(
                order_type=OrderType.LIMIT,
                maker_preference=MakerPreference.MAKER_ONLY,
                execution_params=SingleShotParams(price=Decimal('50000')),
            ),
        )

    def test_maker_only_accepts_limit_ioc(self) -> None:
        validate_trade_command(
            _cmd(
                order_type=OrderType.LIMIT_IOC,
                maker_preference=MakerPreference.MAKER_ONLY,
                execution_params=SingleShotParams(price=Decimal('50000')),
            ),
        )

    def test_maker_only_rejects_market(self) -> None:
        with pytest.raises(ValueError, match='MAKER_ONLY requires order_type in'):
            validate_trade_command(
                _cmd(
                    order_type=OrderType.MARKET,
                    maker_preference=MakerPreference.MAKER_ONLY,
                ),
            )

    def test_maker_only_rejects_stop(self) -> None:
        with pytest.raises(ValueError, match='MAKER_ONLY requires order_type in'):
            validate_trade_command(
                _cmd(
                    order_type=OrderType.STOP,
                    maker_preference=MakerPreference.MAKER_ONLY,
                    execution_params=SingleShotParams(stop_price=Decimal('49000')),
                ),
            )

    def test_maker_preferred_accepts_any(self) -> None:
        validate_trade_command(
            _cmd(
                order_type=OrderType.MARKET,
                maker_preference=MakerPreference.MAKER_PREFERRED,
            ),
        )

    def test_no_preference_accepts_any(self) -> None:
        validate_trade_command(
            _cmd(
                order_type=OrderType.MARKET,
                maker_preference=MakerPreference.NO_PREFERENCE,
            ),
        )


class TestVenueFilters:
    def test_no_filters_passes(self) -> None:
        validate_trade_command(_cmd(order_type=OrderType.MARKET))

    def test_valid_qty_and_price_passes(self) -> None:
        validate_trade_command(
            _cmd(
                order_type=OrderType.LIMIT,
                execution_params=SingleShotParams(price=Decimal('50000.00')),
                qty=Decimal('0.010'),
            ),
            filters=_FILTERS,
        )

    def test_qty_below_lot_min(self) -> None:
        filters = SymbolFilters(
            symbol='BTCUSDT',
            tick_size=Decimal('0.01'),
            lot_step=Decimal('0.0001'),
            lot_min=Decimal('0.001'),
            lot_max=Decimal('100'),
            min_notional=Decimal('10'),
        )
        with pytest.raises(ValueError, match='below lot minimum'):
            validate_trade_command(
                _cmd(order_type=OrderType.MARKET, qty=Decimal('0.0001')),
                filters=filters,
            )

    def test_qty_above_lot_max(self) -> None:
        with pytest.raises(ValueError, match='above lot maximum'):
            validate_trade_command(
                _cmd(order_type=OrderType.MARKET, qty=Decimal('200')),
                filters=_FILTERS,
            )

    def test_qty_not_multiple_of_lot_step(self) -> None:
        with pytest.raises(ValueError, match='not a multiple of lot step'):
            validate_trade_command(
                _cmd(order_type=OrderType.MARKET, qty=Decimal('0.0015')),
                filters=_FILTERS,
            )

    def test_price_not_multiple_of_tick_size(self) -> None:
        with pytest.raises(ValueError, match='not a multiple of tick size'):
            validate_trade_command(
                _cmd(
                    order_type=OrderType.LIMIT,
                    execution_params=SingleShotParams(price=Decimal('50000.005')),
                ),
                filters=_FILTERS,
            )

    def test_notional_below_minimum(self) -> None:
        with pytest.raises(ValueError, match='below minimum'):
            validate_trade_command(
                _cmd(
                    order_type=OrderType.LIMIT,
                    execution_params=SingleShotParams(price=Decimal('100.00')),
                    qty=Decimal('0.001'),
                ),
                filters=_FILTERS,
            )

    def test_market_order_skips_price_checks(self) -> None:
        validate_trade_command(
            _cmd(order_type=OrderType.MARKET, qty=Decimal('0.010')),
            filters=_FILTERS,
        )
