'''
Tests for praxis.core.validate_trade_abort.
'''

from __future__ import annotations

from datetime import datetime, UTC

import pytest

from praxis.core.domain.trade_abort import TradeAbort
from praxis.core.validate_trade_abort import validate_trade_abort

_NOW = datetime.now(UTC)

_ACCEPTED: dict[str, str] = {
    'cmd-001': 'acct-A',
    'cmd-002': 'acct-B',
    'cmd-003': 'acct-A',
}

_TERMINAL: frozenset[str] = frozenset({'cmd-003'})


def _abort(
    command_id: str = 'cmd-001',
    account_id: str = 'acct-A',
) -> TradeAbort:
    return TradeAbort(
        command_id=command_id,
        account_id=account_id,
        reason='test abort',
        created_at=_NOW,
    )


class TestValidAbort:
    def test_returns_true_for_valid_abort(self) -> None:
        assert validate_trade_abort(_abort(), _ACCEPTED, _TERMINAL) is True

    def test_returns_true_for_different_account(self) -> None:
        assert (
            validate_trade_abort(
                _abort(command_id='cmd-002', account_id='acct-B'),
                _ACCEPTED,
                _TERMINAL,
            )
            is True
        )


class TestUnknownCommandId:
    def test_raises_for_unknown_command_id(self) -> None:
        with pytest.raises(ValueError, match='unknown command_id'):
            validate_trade_abort(_abort(command_id='cmd-999'), _ACCEPTED, _TERMINAL)

    def test_raises_when_accepted_is_empty(self) -> None:
        with pytest.raises(ValueError, match='unknown command_id'):
            validate_trade_abort(_abort(), {}, frozenset())


class TestTerminalNoOp:
    def test_returns_false_for_terminal_command(self) -> None:
        assert (
            validate_trade_abort(
                _abort(command_id='cmd-003'),
                _ACCEPTED,
                _TERMINAL,
            )
            is False
        )

    def test_raises_for_mismatched_account_on_terminal(self) -> None:
        with pytest.raises(ValueError, match='account_id mismatch'):
            validate_trade_abort(
                _abort(command_id='cmd-003', account_id='acct-B'),
                _ACCEPTED,
                _TERMINAL,
            )


class TestAccountIdMismatch:
    def test_raises_for_mismatched_account_id(self) -> None:
        with pytest.raises(ValueError, match='account_id mismatch'):
            validate_trade_abort(
                _abort(command_id='cmd-001', account_id='acct-B'),
                _ACCEPTED,
                _TERMINAL,
            )

    def test_raises_for_mismatched_reverse(self) -> None:
        with pytest.raises(ValueError, match='account_id mismatch'):
            validate_trade_abort(
                _abort(command_id='cmd-002', account_id='acct-A'),
                _ACCEPTED,
                _TERMINAL,
            )
