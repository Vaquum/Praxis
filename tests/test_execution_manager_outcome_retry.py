'''Tests for ExecutionManager._dispatch_outcome_with_retry (MAJOR-004).

Pre-fix the on_trade_outcome callback exception was logged and
swallowed once, leaving TradeOutcomeProduced durably on the spine
but the consumer (Nexus) unaware. Post-fix the callback is retried
up to N attempts with exponential backoff before giving up.

The helper is exercised in isolation here (no submit_command driver)
so the asyncio.sleep mock cannot starve the worker task.
'''

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, patch

import pytest

from praxis.core.domain.enums import TradeStatus
from praxis.core.domain.trade_outcome import TradeOutcome
from praxis.core.execution_manager import (
    _OUTCOME_CALLBACK_BASE_DELAY,
    _OUTCOME_CALLBACK_MAX_ATTEMPTS,
    ExecutionManager,
)
from praxis.infrastructure.event_spine import EventSpine
from praxis.infrastructure.venue_adapter import VenueAdapter

_TS = datetime(2099, 1, 1, tzinfo=UTC)


def _outcome() -> TradeOutcome:
    return TradeOutcome(
        command_id='cmd-retry-001',
        trade_id='trade-retry-001',
        account_id='acc-retry',
        status=TradeStatus.FILLED,
        target_qty=Decimal('1'),
        filled_qty=Decimal('1'),
        avg_fill_price=Decimal('50000'),
        slices_completed=1,
        slices_total=1,
        reason=None,
        created_at=_TS,
        cumulative_notional=Decimal('50000'),
    )


def _make_mgr(
    spine: EventSpine,
    callback: AsyncMock | None,
) -> ExecutionManager:
    adapter = AsyncMock(spec=VenueAdapter)
    return ExecutionManager(
        event_spine=spine,
        epoch_id=1,
        venue_adapter=adapter,
        on_trade_outcome=callback,
    )


class TestDispatchOutcomeWithRetry:

    @pytest.mark.asyncio
    async def test_success_on_first_attempt_no_retry(
        self, spine: EventSpine,
    ) -> None:
        callback = AsyncMock()
        mgr = _make_mgr(spine, callback)

        with patch(
            'praxis.core.execution_manager.asyncio.sleep',
            new_callable=AsyncMock,
        ) as mock_sleep:
            await mgr._dispatch_outcome_with_retry(_outcome(), source='test')

        assert callback.await_count == 1
        mock_sleep.assert_not_called()

    @pytest.mark.asyncio
    async def test_transient_failure_retries_then_succeeds(
        self, spine: EventSpine,
    ) -> None:
        callback = AsyncMock(side_effect=[RuntimeError('transient'), None])
        mgr = _make_mgr(spine, callback)

        with patch(
            'praxis.core.execution_manager.asyncio.sleep',
            new_callable=AsyncMock,
        ) as mock_sleep:
            await mgr._dispatch_outcome_with_retry(_outcome(), source='test')

        assert callback.await_count == 2
        mock_sleep.assert_awaited_once_with(_OUTCOME_CALLBACK_BASE_DELAY)

    @pytest.mark.asyncio
    async def test_persistent_failure_exhausts_attempts_no_raise(
        self, spine: EventSpine,
    ) -> None:
        callback = AsyncMock(side_effect=RuntimeError('persistent'))
        mgr = _make_mgr(spine, callback)

        with patch(
            'praxis.core.execution_manager.asyncio.sleep',
            new_callable=AsyncMock,
        ) as mock_sleep:
            await mgr._dispatch_outcome_with_retry(_outcome(), source='test')

        assert callback.await_count == _OUTCOME_CALLBACK_MAX_ATTEMPTS
        expected_delays = [
            _OUTCOME_CALLBACK_BASE_DELAY * (2 ** i)
            for i in range(_OUTCOME_CALLBACK_MAX_ATTEMPTS - 1)
        ]
        actual_delays = [c.args[0] for c in mock_sleep.await_args_list]
        assert actual_delays == expected_delays

    @pytest.mark.asyncio
    async def test_no_callback_wired_is_noop(self, spine: EventSpine) -> None:
        mgr = _make_mgr(spine, callback=None)

        with patch(
            'praxis.core.execution_manager.asyncio.sleep',
            new_callable=AsyncMock,
        ) as mock_sleep:
            await mgr._dispatch_outcome_with_retry(_outcome(), source='test')

        mock_sleep.assert_not_called()
