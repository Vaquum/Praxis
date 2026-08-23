'''
Tests for the TradeModify envelope (WP-Praxis-0009).
'''

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest

from praxis.core.domain.iceberg_modify import IcebergModify
from praxis.core.domain.trade_modify import TradeModify

_TS = datetime(2099, 1, 1, tzinfo=UTC)
_ACCT = 'acc-1'
_CMD = '11111111-2222-3333-4444-555555555555'


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


class TestTradeModifyEnvelope:

    def test_constructs_with_valid_fields(self) -> None:
        modify = _modify()

        assert modify.command_id == _CMD
        assert isinstance(modify.modify_params, IcebergModify)

    def test_empty_command_id_rejected(self) -> None:
        with pytest.raises(ValueError, match='command_id'):
            _modify(command_id='')

    def test_naive_created_at_rejected(self) -> None:
        with pytest.raises(ValueError, match='timezone-aware'):
            _modify(created_at=datetime(2099, 1, 1))
