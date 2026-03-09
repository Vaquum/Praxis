'''
Tests for praxis.core.generate_client_order_id.
'''

from __future__ import annotations

import pytest

from praxis.core.domain.enums import ExecutionMode
from praxis.core.generate_client_order_id import generate_client_order_id

_UUID = '550e8400-e29b-41d4-a716-446655440000'
_HEX16 = '550e8400e29b41d4'


class TestModePrefix:
    @pytest.mark.parametrize(
        ('mode', 'prefix'),
        [
            (ExecutionMode.SINGLE_SHOT, 'SS'),
            (ExecutionMode.BRACKET, 'BK'),
            (ExecutionMode.TWAP, 'TW'),
            (ExecutionMode.SCHEDULED_VWAP, 'SV'),
            (ExecutionMode.ICEBERG, 'IC'),
            (ExecutionMode.TIME_DCA, 'TD'),
            (ExecutionMode.LADDER_DCA, 'LD'),
        ],
    )
    def test_all_modes_produce_correct_prefix(
        self, mode: ExecutionMode, prefix: str
    ) -> None:
        result = generate_client_order_id(mode, _UUID, 0)
        assert result.startswith(f'{prefix}-')


class TestFormat:
    def test_output_matches_expected_pattern(self) -> None:
        result = generate_client_order_id(ExecutionMode.TWAP, _UUID, 47)
        assert result == f'TW-{_HEX16}-047'

    def test_deterministic_same_inputs_same_output(self) -> None:
        a = generate_client_order_id(ExecutionMode.BRACKET, _UUID, 5, retry=1)
        b = generate_client_order_id(ExecutionMode.BRACKET, _UUID, 5, retry=1)
        assert a == b

    def test_truncates_command_id_to_16_hex(self) -> None:
        result = generate_client_order_id(ExecutionMode.SINGLE_SHOT, _UUID, 0)
        mid = result.split('-', 1)[1].rsplit('-', 1)[0]
        assert mid == _HEX16
        assert len(mid) == 16


class TestSequence:
    def test_zero_pads_single_digit(self) -> None:
        result = generate_client_order_id(ExecutionMode.TWAP, _UUID, 0)
        assert result.endswith('-000')

    def test_zero_pads_double_digit(self) -> None:
        result = generate_client_order_id(ExecutionMode.TWAP, _UUID, 47)
        assert result.endswith('-047')

    def test_triple_digit_no_padding(self) -> None:
        result = generate_client_order_id(ExecutionMode.TWAP, _UUID, 999)
        assert result.endswith('-999')


class TestRetry:
    def test_retry_zero_no_suffix(self) -> None:
        result = generate_client_order_id(ExecutionMode.TWAP, _UUID, 1, retry=0)
        assert result == f'TW-{_HEX16}-001'

    def test_retry_positive_appends_suffix(self) -> None:
        result = generate_client_order_id(ExecutionMode.TWAP, _UUID, 1, retry=3)
        assert result == f'TW-{_HEX16}-001r3'

    def test_retry_double_digit(self) -> None:
        result = generate_client_order_id(ExecutionMode.TWAP, _UUID, 1, retry=12)
        assert result == f'TW-{_HEX16}-001r12'


class TestLength:
    @pytest.mark.parametrize('mode', list(ExecutionMode))
    def test_all_modes_within_36_chars(self, mode: ExecutionMode) -> None:
        result = generate_client_order_id(mode, _UUID, 999, retry=99)
        assert len(result) <= 36


class TestValidation:
    def test_negative_sequence_raises(self) -> None:
        with pytest.raises(ValueError, match='sequence must be between 0 and 999'):
            generate_client_order_id(ExecutionMode.TWAP, _UUID, -1)

    def test_sequence_exceeds_max_raises(self) -> None:
        with pytest.raises(ValueError, match='sequence must be between 0 and 999'):
            generate_client_order_id(ExecutionMode.TWAP, _UUID, 1000)

    def test_negative_retry_raises(self) -> None:
        with pytest.raises(ValueError, match='retry must be non-negative'):
            generate_client_order_id(ExecutionMode.TWAP, _UUID, 0, retry=-1)

    def test_short_command_id_raises(self) -> None:
        with pytest.raises(
            ValueError, match='command_id must contain at least 16 hex characters'
        ):
            generate_client_order_id(ExecutionMode.TWAP, 'abc', 0)
