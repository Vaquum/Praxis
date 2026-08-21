'''
Tests for the per-mode amend parameter dataclasses and the
MODIFY_PARAMS_FOR_MODE registry (WP-Praxis-0009).
'''

from __future__ import annotations

from decimal import Decimal

import pytest

from praxis.core.domain.bracket_modify import BracketModify
from praxis.core.domain.enums import ExecutionMode
from praxis.core.domain.iceberg_modify import IcebergModify
from praxis.core.domain.ladder_dca_modify import LadderDcaModify
from praxis.core.domain.modify_params import MODIFY_PARAMS_FOR_MODE, ModifyParams
from praxis.core.domain.scheduled_vwap_modify import ScheduledVwapModify
from praxis.core.domain.single_shot_modify import SingleShotModify
from praxis.core.domain.time_dca_modify import TimeDcaModify
from praxis.core.domain.twap_modify import TwapModify


class TestPartialAmend:

    def test_single_shot_amends_price_only(self) -> None:
        modify = SingleShotModify(price=Decimal('50000'))

        assert modify.price == Decimal('50000')
        assert modify.stop_price is None

    def test_iceberg_amends_display_only(self) -> None:
        modify = IcebergModify(display_qty=Decimal('0.2'))

        assert modify.display_qty == Decimal('0.2')
        assert modify.limit_price is None

    def test_twap_amends_interval_only(self) -> None:
        modify = TwapModify(interval_seconds=30)

        assert modify.interval_seconds == 30
        assert modify.num_slices is None


class TestEmptyAmendRejected:

    @pytest.mark.parametrize('factory', [
        SingleShotModify,
        BracketModify,
        IcebergModify,
        LadderDcaModify,
        TwapModify,
        TimeDcaModify,
        ScheduledVwapModify,
    ])
    def test_all_none_rejected(self, factory: type[ModifyParams]) -> None:
        with pytest.raises(ValueError, match='at least one field'):
            factory()


class TestFieldValidation:

    def test_non_positive_price_rejected(self) -> None:
        with pytest.raises(ValueError, match='positive'):
            IcebergModify(limit_price=Decimal('0'))

    def test_bracket_price_and_offset_mutually_exclusive(self) -> None:
        with pytest.raises(ValueError, match='not both'):
            BracketModify(
                take_profit_price=Decimal('51000'),
                take_profit_offset_bps=Decimal('50'),
            )

    def test_ladder_non_monotonic_rejected(self) -> None:
        with pytest.raises(ValueError, match='monotonic'):
            LadderDcaModify(price_levels=(Decimal('50000'), Decimal('50000')))

    def test_ladder_weights_must_sum_to_one(self) -> None:
        with pytest.raises(ValueError, match='sum to 1'):
            LadderDcaModify(level_weights=(Decimal('0.5'), Decimal('0.4')))

    def test_ladder_levels_and_weights_length_must_match(self) -> None:
        with pytest.raises(ValueError, match='match price_levels in length'):
            LadderDcaModify(
                price_levels=(Decimal('49000'), Decimal('48000')),
                level_weights=(Decimal('0.4'), Decimal('0.3'), Decimal('0.3')),
            )

    def test_vwap_weights_must_sum_to_one(self) -> None:
        with pytest.raises(ValueError, match='sum to 1'):
            ScheduledVwapModify(volume_weights=(Decimal('0.5'), Decimal('0.4')))

    def test_twap_num_slices_below_minimum_rejected(self) -> None:
        with pytest.raises(ValueError, match='at least 2'):
            TwapModify(num_slices=1)

    def test_twap_non_positive_interval_rejected(self) -> None:
        with pytest.raises(ValueError, match='positive int'):
            TwapModify(interval_seconds=0)


class TestRegistry:

    def test_every_mode_has_a_modify_type(self) -> None:
        assert set(MODIFY_PARAMS_FOR_MODE) == set(ExecutionMode)

    def test_registry_maps_to_expected_types(self) -> None:
        assert MODIFY_PARAMS_FOR_MODE[ExecutionMode.ICEBERG] is IcebergModify
        assert MODIFY_PARAMS_FOR_MODE[ExecutionMode.TWAP] is TwapModify
        assert MODIFY_PARAMS_FOR_MODE[ExecutionMode.BRACKET] is BracketModify


class TestBoolRejectedAsInt:

    def test_twap_interval_rejects_bool(self) -> None:
        with pytest.raises(ValueError, match='interval_seconds'):
            TwapModify(interval_seconds=True)

    def test_twap_num_slices_rejects_bool(self) -> None:
        with pytest.raises(ValueError, match='num_slices'):
            TwapModify(num_slices=True)

    def test_time_dca_interval_rejects_bool(self) -> None:
        with pytest.raises(ValueError, match='interval_seconds'):
            TimeDcaModify(interval_seconds=True)

    def test_time_dca_iterations_rejects_bool(self) -> None:
        with pytest.raises(ValueError, match='num_iterations'):
            TimeDcaModify(num_iterations=True)

    def test_scheduled_vwap_interval_rejects_bool(self) -> None:
        with pytest.raises(ValueError, match='interval_seconds'):
            ScheduledVwapModify(interval_seconds=True)
