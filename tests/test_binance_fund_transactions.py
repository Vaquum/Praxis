'''Tests for BinanceAdapter.query_fund_transactions (WP-Praxis-0009).'''

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

import pytest

from praxis.infrastructure.binance_adapter import BinanceAdapter
from praxis.infrastructure.secret_store import Credentials
from praxis.infrastructure.venue_adapter import VenueFundTransaction

_ACCT = 'acc-1'

_DEPOSITS: list[dict[str, Any]] = [
    {'id': 'dep-1', 'coin': 'USDT', 'amount': '1000.5',
     'insertTime': 1700000000000, 'status': 1},
    {'id': 'dep-2', 'coin': 'USDT', 'amount': '50',
     'insertTime': 1700000100000, 'status': 0},
]
_WITHDRAWALS: list[dict[str, Any]] = [
    {'id': 'wd-1', 'coin': 'USDT', 'amount': '200',
     'applyTime': '2023-11-14 22:14:00', 'status': 6},
    {'id': 'wd-2', 'coin': 'USDT', 'amount': '10',
     'applyTime': '2023-11-14 22:20:00', 'status': 3},
]


def _adapter() -> BinanceAdapter:
    creds = {_ACCT: Credentials(api_key='k', api_secret='s')}
    return BinanceAdapter('https://api.test', 'wss://s.test', 'wss://a.test', creds)


async def _route(_method: str, path: str, _params: dict[str, str], _account_id: str, **_kw: Any) -> Any:
    if 'deposit' in path:
        return _DEPOSITS
    if 'withdraw' in path:
        return _WITHDRAWALS
    raise AssertionError(path)


class TestQueryFundTransactions:

    @pytest.mark.asyncio
    async def test_parses_and_filters_settled(self) -> None:
        adapter = _adapter()
        adapter._signed_request = _route  # type: ignore[method-assign]

        result = await adapter.query_fund_transactions(_ACCT)

        assert [t.fund_transaction_id for t in result] == ['dep-1', 'wd-1']

        deposit = result[0]
        assert deposit.direction == 'DEPOSIT'
        assert deposit.asset == 'USDT'
        assert deposit.amount == Decimal('1000.5')
        assert deposit.timestamp == datetime.fromtimestamp(1700000000, tz=UTC)

        withdrawal = result[1]
        assert withdrawal.direction == 'WITHDRAWAL'
        assert withdrawal.amount == Decimal('200')
        assert withdrawal.timestamp == datetime(2023, 11, 14, 22, 14, tzinfo=UTC)

    @pytest.mark.asyncio
    async def test_binsim_returns_empty_without_request(
        self, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setenv('BINSIM_URL', 'http://binsim')
        adapter = _adapter()
        called = False

        async def _fail(*_a: Any, **_k: Any) -> Any:
            nonlocal called
            called = True
            return []

        adapter._signed_request = _fail  # type: ignore[method-assign]

        assert await adapter.query_fund_transactions(_ACCT) == []
        assert called is False

    @pytest.mark.asyncio
    async def test_naive_start_time_rejected(self) -> None:
        adapter = _adapter()

        with pytest.raises(ValueError, match='start_time'):
            await adapter.query_fund_transactions(
                _ACCT, start_time=datetime(2023, 1, 1),
            )


class TestVenueFundTransaction:

    def test_naive_timestamp_rejected(self) -> None:
        with pytest.raises(ValueError, match='timezone-aware'):
            VenueFundTransaction(
                fund_transaction_id='x', asset='USDT', amount=Decimal('1'),
                direction='DEPOSIT', timestamp=datetime(2023, 1, 1),
            )

    def test_non_positive_amount_rejected(self) -> None:
        with pytest.raises(ValueError, match='positive finite Decimal'):
            VenueFundTransaction(
                fund_transaction_id='x', asset='USDT', amount=Decimal('0'),
                direction='DEPOSIT', timestamp=datetime(2023, 1, 1, tzinfo=UTC),
            )

    def test_bad_direction_rejected(self) -> None:
        with pytest.raises(ValueError, match='direction must be one of'):
            VenueFundTransaction(
                fund_transaction_id='x', asset='USDT', amount=Decimal('1'),
                direction='TRANSFER', timestamp=datetime(2023, 1, 1, tzinfo=UTC),
            )
