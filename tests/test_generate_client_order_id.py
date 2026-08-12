'''
Tests for praxis.core.generate_client_order_id.
'''

from __future__ import annotations

import pytest

from praxis.core.domain.enums import ExecutionMode
from praxis.core.generate_client_order_id import (
    command_id_fragment,
    generate_client_order_id,
    praxis_command_fragment,
)

_UUID = '550e8400-e29b-41d4-a716-446655440000'
_HEX16 = '550e8400e29b41d4'


class TestCommandIdFragment:
    def test_strips_hyphens_and_truncates(self) -> None:
        assert command_id_fragment(_UUID) == _HEX16

    def test_non_hex_fragment_preserved(self) -> None:
        assert command_id_fragment('nexus_1234567890abcdef') == 'nexus_1234567890'


class TestPraxisCommandFragment:
    @pytest.mark.parametrize('mode', list(ExecutionMode))
    def test_extracts_fragment_from_own_ids(self, mode: ExecutionMode) -> None:
        assert praxis_command_fragment(
            generate_client_order_id(mode, _UUID, 7),
        ) == _HEX16

    def test_extracts_fragment_with_retry(self) -> None:
        assert praxis_command_fragment(
            generate_client_order_id(ExecutionMode.TWAP, _UUID, 7, retry=3),
        ) == _HEX16

    def test_non_hex_command_fragment_round_trips(self) -> None:
        command_id = 'nexus_1234567890abcdef'
        client_order_id = generate_client_order_id(
            ExecutionMode.SINGLE_SHOT, command_id, 0,
        )

        assert praxis_command_fragment(client_order_id) == command_id_fragment(
            command_id,
        )

    @pytest.mark.parametrize(
        'foreign',
        [
            'web_manual_order_1',
            'x-ABC123',
            '123456789',
            'SS-tooShort-00',
            'ZZ-550e8400e29b41d4-000',
            '',
        ],
    )
    def test_returns_none_for_foreign_ids(self, foreign: str) -> None:
        assert praxis_command_fragment(foreign) is None


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
        assert result.startswith(f"{prefix}-")


class TestFormat:
    def test_output_matches_expected_pattern(self) -> None:
        result = generate_client_order_id(ExecutionMode.TWAP, _UUID, 47)
        assert result == f"TW-{_HEX16}-047"

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
        assert result == f"TW-{_HEX16}-001"

    def test_retry_positive_appends_suffix(self) -> None:
        result = generate_client_order_id(ExecutionMode.TWAP, _UUID, 1, retry=3)
        assert result == f"TW-{_HEX16}-001r3"

    def test_retry_double_digit(self) -> None:
        result = generate_client_order_id(ExecutionMode.TWAP, _UUID, 1, retry=12)
        assert result == f"TW-{_HEX16}-001r12"


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
            ValueError, match='command_id must have at least 16 characters'
        ):
            generate_client_order_id(ExecutionMode.TWAP, 'abc', 0)
