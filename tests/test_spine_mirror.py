'''
Tests for observability.spine_mirror.
'''

from __future__ import annotations

import importlib.util
import sys
from datetime import UTC, datetime
from pathlib import Path
from types import ModuleType, SimpleNamespace
from unittest.mock import MagicMock

import pytest


class _StubDatabaseError(Exception):
    pass


class _StubOperationalError(Exception):
    pass


_stub_clickhouse_connect = ModuleType('clickhouse_connect')
_stub_clickhouse_connect_driver = ModuleType('clickhouse_connect.driver')
_stub_clickhouse_connect_exceptions = ModuleType('clickhouse_connect.driver.exceptions')

_stub_clickhouse_connect_exceptions.DatabaseError = _StubDatabaseError
_stub_clickhouse_connect_exceptions.OperationalError = _StubOperationalError
_stub_clickhouse_connect_driver.exceptions = _stub_clickhouse_connect_exceptions
_stub_clickhouse_connect_driver.Client = MagicMock
_stub_clickhouse_connect.driver = _stub_clickhouse_connect_driver

sys.modules.setdefault('clickhouse_connect', _stub_clickhouse_connect)
sys.modules.setdefault('clickhouse_connect.driver', _stub_clickhouse_connect_driver)
sys.modules.setdefault(
    'clickhouse_connect.driver.exceptions', _stub_clickhouse_connect_exceptions,
)


_MIRROR_PATH = (
    Path(__file__).resolve().parent.parent / 'observability' / 'spine_mirror.py'
)
_spec = importlib.util.spec_from_file_location('spine_mirror', _MIRROR_PATH)
assert _spec is not None
assert _spec.loader is not None
spine_mirror = importlib.util.module_from_spec(_spec)
sys.modules['spine_mirror'] = spine_mirror
_spec.loader.exec_module(spine_mirror)


class TestParseTs:

    def test_utc_offset(self) -> None:

        result = spine_mirror._parse_ts('2026-06-04T10:00:00+00:00')

        assert result == datetime(2026, 6, 4, 10, 0, 0, tzinfo=UTC)

    def test_zulu_suffix(self) -> None:

        result = spine_mirror._parse_ts('2026-06-04T10:00:00Z')

        assert result == datetime(2026, 6, 4, 10, 0, 0, tzinfo=UTC)

    def test_naive_assumes_utc(self) -> None:

        result = spine_mirror._parse_ts('2026-06-04T10:00:00')

        assert result == datetime(2026, 6, 4, 10, 0, 0, tzinfo=UTC)

    def test_negative_offset_converts_instant(self) -> None:

        result = spine_mirror._parse_ts('2026-06-04T10:00:00-05:00')

        assert result == datetime(2026, 6, 4, 15, 0, 0, tzinfo=UTC)

    def test_positive_offset_converts_instant(self) -> None:

        result = spine_mirror._parse_ts('2026-06-04T10:00:00+05:30')

        assert result == datetime(2026, 6, 4, 4, 30, 0, tzinfo=UTC)

    def test_microseconds_preserved(self) -> None:

        result = spine_mirror._parse_ts('2026-06-04T10:00:00.123456+00:00')

        assert result == datetime(2026, 6, 4, 10, 0, 0, 123456, tzinfo=UTC)


class TestBackoffSeconds:

    def test_first_failure_returns_base(self) -> None:

        assert spine_mirror._backoff_seconds(1) == spine_mirror._BACKOFF_BASE_S

    def test_doubles_each_consecutive_failure(self) -> None:

        s1 = spine_mirror._backoff_seconds(1)
        s2 = spine_mirror._backoff_seconds(2)
        s3 = spine_mirror._backoff_seconds(3)

        assert s2 == s1 * 2
        assert s3 == s2 * 2

    def test_clamps_at_backoff_max(self) -> None:

        result = spine_mirror._backoff_seconds(50)

        assert result == spine_mirror._BACKOFF_MAX_S

    def test_clamp_boundary_at_max(self) -> None:

        for failures in (20, 25, 100):
            assert spine_mirror._backoff_seconds(failures) == spine_mirror._BACKOFF_MAX_S


class TestToRows:

    def test_str_payload_passes_through(self) -> None:

        raw_rows = [(1, 5, '2026-06-04T10:00:00+00:00', 'CommandAccepted', '{"strategy_id": "s1"}')]

        result = spine_mirror._to_rows(raw_rows)

        assert result == [[
            1, 5, datetime(2026, 6, 4, 10, 0, 0, tzinfo=UTC),
            'CommandAccepted', '{"strategy_id": "s1"}',
        ]]

    def test_bytes_payload_decoded(self) -> None:

        raw_rows = [(2, 5, '2026-06-04T10:00:00+00:00', 'FillReceived', b'{"qty": "0.1"}')]

        result = spine_mirror._to_rows(raw_rows)

        assert result[0][4] == '{"qty": "0.1"}'

    def test_bytes_with_invalid_utf8_replaced(self) -> None:

        raw_rows = [(3, 5, '2026-06-04T10:00:00+00:00', 'OrderRejected', b'\xff\xfeplain')]

        result = spine_mirror._to_rows(raw_rows)

        assert 'plain' in result[0][4]

    def test_integer_coercion(self) -> None:

        raw_rows = [(1, 5, '2026-06-04T10:00:00+00:00', 'CommandAccepted', '{}')]

        result = spine_mirror._to_rows(raw_rows)

        assert isinstance(result[0][0], int)
        assert isinstance(result[0][1], int)


class TestCurrentCursor:

    def test_empty_table_returns_zero(self) -> None:

        ch = MagicMock()
        ch.query.return_value = SimpleNamespace(result_rows=[])

        result = spine_mirror._current_cursor(ch, 'praxis')

        assert result == 0
        ch.query.assert_called_once_with('SELECT max(event_seq) FROM praxis.events')

    def test_null_aggregate_returns_zero(self) -> None:

        ch = MagicMock()
        ch.query.return_value = SimpleNamespace(result_rows=[(None,)])

        result = spine_mirror._current_cursor(ch, 'praxis')

        assert result == 0

    def test_populated_table_returns_max_seq(self) -> None:

        ch = MagicMock()
        ch.query.return_value = SimpleNamespace(result_rows=[(42_000_000,)])

        result = spine_mirror._current_cursor(ch, 'praxis')

        assert result == 42_000_000

    def test_database_name_in_query(self) -> None:

        ch = MagicMock()
        ch.query.return_value = SimpleNamespace(result_rows=[(7,)])

        spine_mirror._current_cursor(ch, 'praxis_test')

        ch.query.assert_called_once_with('SELECT max(event_seq) FROM praxis_test.events')


class TestIdentifierRegex:

    @pytest.mark.parametrize('name', ['praxis', 'PRAXIS', 'p1', 'a_b_c', '_underscore', 'p123'])
    def test_accepts_safe_identifiers(self, name: str) -> None:

        assert spine_mirror._IDENTIFIER_RE.fullmatch(name) is not None

    @pytest.mark.parametrize(
        'name',
        ['', '1praxis', 'praxis-test', 'praxis test', 'praxis;', 'praxis.events',
         "praxis'", 'praxis`', 'praxis$', 'praxis/foo'],
    )
    def test_rejects_unsafe_identifiers(self, name: str) -> None:

        assert spine_mirror._IDENTIFIER_RE.fullmatch(name) is None


class TestEnsureSchema:

    def test_issues_create_database_then_create_table(self) -> None:

        ch = MagicMock()

        spine_mirror._ensure_schema(ch, 'praxis')

        assert ch.command.call_count == 2

        first_call = ch.command.call_args_list[0].args[0]
        second_call = ch.command.call_args_list[1].args[0]

        assert first_call == 'CREATE DATABASE IF NOT EXISTS praxis'
        assert 'CREATE TABLE IF NOT EXISTS praxis.events' in second_call

    def test_uses_supplied_database_name(self) -> None:

        ch = MagicMock()

        spine_mirror._ensure_schema(ch, 'praxis_test')

        first_call = ch.command.call_args_list[0].args[0]
        second_call = ch.command.call_args_list[1].args[0]

        assert first_call == 'CREATE DATABASE IF NOT EXISTS praxis_test'
        assert 'CREATE TABLE IF NOT EXISTS praxis_test.events' in second_call
