from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncGenerator
from datetime import datetime, UTC
from decimal import Decimal
from typing import Any
from typing import cast
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio

from praxis.core.domain.enums import (
    ExecutionMode,
    MakerPreference,
    OrderSide,
    OrderStatus,
    OrderType,
    STPMode,
    TradeStatus,
)
from praxis.core.domain.single_shot_params import SingleShotParams
from praxis.core.domain.trade_command import TradeCommand
from praxis.core.estimate_slippage import SlippageEstimate
from praxis.core.execution_manager import ExecutionManager
from praxis.infrastructure.event_spine import EventSpine
from praxis.core.domain.events import TradeOutcomeProduced
from praxis.core.domain.trade_outcome import TradeOutcome
from praxis.launcher import _trade_outcome_from_produced
from praxis.infrastructure.venue_adapter import (
    ImmediateFill,
    OrderBookLevel,
    OrderBookSnapshot,
    SubmitResult,
    TransientError,
    VenueAdapter,
)

_TS = datetime(2099, 1, 1, tzinfo=UTC)
_ACCT = 'acc-1'
_TRADE = 'trade-1'
_EPOCH = 1

_CMD_KWARGS: dict[str, Any] = {
    'trade_id': _TRADE,
    'account_id': _ACCT,
    'symbol': 'BTCUSDT',
    'side': OrderSide.BUY,
    'qty': Decimal('1'),
    'order_type': OrderType.LIMIT,
    'execution_mode': ExecutionMode.SINGLE_SHOT,
    'execution_params': SingleShotParams(price=Decimal('50000')),
    'timeout': 300,
    'reference_price': None,
    'maker_preference': MakerPreference.NO_PREFERENCE,
    'stp_mode': STPMode.NONE,
    'created_at': _TS,
}


def _extract_decimal_arg(record: logging.LogRecord, index: int) -> Decimal:
    args = cast(tuple[Any, ...], record.args)
    return cast(Decimal, args[index])



@pytest.fixture
def adapter() -> AsyncMock:
    mock = AsyncMock(spec=VenueAdapter)
    mock.submit_order.return_value = SubmitResult(
        venue_order_id='venue-1',
        status=OrderStatus.OPEN,
        immediate_fills=(),
    )
    mock.query_order_book.return_value = OrderBookSnapshot(
        bids=(OrderBookLevel(price=Decimal('49990'), qty=Decimal('2')),),
        asks=(OrderBookLevel(price=Decimal('50010'), qty=Decimal('2')),),
        last_update_id=1,
    )
    return mock


@pytest_asyncio.fixture
async def mgr(
    spine: EventSpine,
    adapter: AsyncMock,
) -> AsyncGenerator[ExecutionManager, None]:
    manager = ExecutionManager(
        event_spine=spine, epoch_id=_EPOCH, venue_adapter=adapter
    )
    yield manager
    for account_id in list(manager._accounts.keys()):
        await manager.unregister_account(account_id)


@pytest.mark.asyncio
async def test_logs_slippage_estimate_metrics(
    mgr: ExecutionManager,
    caplog: pytest.LogCaptureFixture,
) -> None:
    mgr.register_account(_ACCT)
    with caplog.at_level(logging.INFO):
        await mgr.submit_command(**_CMD_KWARGS)
        await asyncio.sleep(0.3)

    matching = [
        record
        for record in caplog.records
        if record.msg.startswith('slippage estimate computed:')
    ]
    assert len(matching) == 1
    slippage_bps = _extract_decimal_arg(matching[0], 2)
    assert slippage_bps == Decimal('2')


@pytest.mark.asyncio
async def test_submission_proceeds_when_order_book_query_fails(
    spine: EventSpine,
    mgr: ExecutionManager,
    adapter: AsyncMock,
    caplog: pytest.LogCaptureFixture,
) -> None:
    adapter.query_order_book.side_effect = TransientError('depth unavailable')
    mgr.register_account(_ACCT)

    with caplog.at_level(logging.WARNING):
        await mgr.submit_command(**_CMD_KWARGS)
        await asyncio.sleep(0.3)

    events = await spine.read(_EPOCH, after_seq=0)
    types = [type(e).__name__ for _, e in events]
    assert types == [
        'CommandAccepted',
        'OrderSubmitIntent',
        'OrderSubmitted',
        'TradeOutcomeProduced',
    ]
    messages = [r.message for r in caplog.records]
    assert any('slippage estimate skipped:' in message for message in messages)


@pytest.mark.asyncio
async def test_capped_submission_rejected_when_order_book_query_fails(
    spine: EventSpine,
    adapter: AsyncMock,
) -> None:
    adapter.query_order_book.side_effect = TransientError('depth unavailable')
    manager = ExecutionManager(
        event_spine=spine, epoch_id=_EPOCH, venue_adapter=adapter,
        max_slippage_bps=Decimal('20'),
    )
    manager.register_account(_ACCT)
    try:
        await manager.submit_command(**{
            **_CMD_KWARGS,
            'order_type': OrderType.MARKET,
            'execution_params': SingleShotParams(),
        })
        await asyncio.sleep(0.3)

        events = await spine.read(_EPOCH, after_seq=0)
        types = [type(e).__name__ for _, e in events]
        assert 'OrderSubmitIntent' not in types
        outcome = next(e for _, e in events if type(e).__name__ == 'TradeOutcomeProduced')
        assert outcome.status is TradeStatus.REJECTED
        adapter.submit_order.assert_not_called()
    finally:
        await manager.unregister_account(_ACCT)


@pytest.mark.asyncio
async def test_capped_submission_rejected_on_partial_book_depth(
    spine: EventSpine,
    adapter: AsyncMock,
) -> None:
    adapter.query_order_book.return_value = OrderBookSnapshot(
        bids=(OrderBookLevel(price=Decimal('49990'), qty=Decimal('5')),),
        asks=(OrderBookLevel(price=Decimal('50010'), qty=Decimal('0.2')),),
        last_update_id=1,
    )
    manager = ExecutionManager(
        event_spine=spine, epoch_id=_EPOCH, venue_adapter=adapter,
        max_slippage_bps=Decimal('20'),
    )
    manager.register_account(_ACCT)
    try:
        await manager.submit_command(**{
            **_CMD_KWARGS,
            'order_type': OrderType.MARKET,
            'execution_params': SingleShotParams(),
        })
        await asyncio.sleep(0.3)

        events = await spine.read(_EPOCH, after_seq=0)
        types = [type(e).__name__ for _, e in events]
        assert 'OrderSubmitIntent' not in types
        outcome = next(e for _, e in events if type(e).__name__ == 'TradeOutcomeProduced')
        assert outcome.status is TradeStatus.REJECTED
        adapter.submit_order.assert_not_called()
    finally:
        await manager.unregister_account(_ACCT)


@pytest.mark.asyncio
async def test_logs_arrival_slippage_when_estimate_is_unavailable(
    mgr: ExecutionManager,
    adapter: AsyncMock,
    caplog: pytest.LogCaptureFixture,
) -> None:
    adapter.query_order_book.side_effect = TransientError('depth unavailable')
    adapter.submit_order.return_value = SubmitResult(
        venue_order_id='venue-3',
        status=OrderStatus.FILLED,
        immediate_fills=(
            ImmediateFill(
                venue_trade_id='t-4',
                qty=Decimal('1'),
                price=Decimal('50020'),
                fee=Decimal('0.001'),
                fee_asset='BTC',
                is_maker=False,
            ),
        ),
    )
    mgr.register_account(_ACCT)

    with caplog.at_level(logging.INFO):
        await mgr.submit_command(
            **{**_CMD_KWARGS, 'reference_price': Decimal('49950')},
        )
        await asyncio.sleep(0.3)

    arrival_records = [
        record
        for record in caplog.records
        if record.msg.startswith('arrival slippage computed:')
    ]
    execution_records = [
        record
        for record in caplog.records
        if record.msg.startswith('execution slippage computed:')
    ]
    assert len(arrival_records) == 1
    assert len(execution_records) == 0


@pytest.mark.asyncio
async def test_logs_execution_slippage_bps_after_fill(
    mgr: ExecutionManager,
    adapter: AsyncMock,
    caplog: pytest.LogCaptureFixture,
) -> None:
    adapter.submit_order.return_value = SubmitResult(
        venue_order_id='venue-1',
        status=OrderStatus.FILLED,
        immediate_fills=(
            ImmediateFill(
                venue_trade_id='t-1',
                qty=Decimal('1'),
                price=Decimal('50020'),
                fee=Decimal('0.001'),
                fee_asset='BTC',
                is_maker=False,
            ),
        ),
    )
    mgr.register_account(_ACCT)
    with caplog.at_level(logging.INFO):
        await mgr.submit_command(**_CMD_KWARGS)
        await asyncio.sleep(0.3)

    matching = [
        record
        for record in caplog.records
        if record.msg.startswith('execution slippage computed:')
    ]
    assert len(matching) == 1
    execution_slippage_bps = _extract_decimal_arg(matching[0], 2)
    assert execution_slippage_bps == Decimal('4')


@pytest.mark.asyncio
async def test_logs_arrival_slippage_bps_when_reference_price_present(
    mgr: ExecutionManager,
    adapter: AsyncMock,
    caplog: pytest.LogCaptureFixture,
) -> None:
    adapter.submit_order.return_value = SubmitResult(
        venue_order_id='venue-1',
        status=OrderStatus.FILLED,
        immediate_fills=(
            ImmediateFill(
                venue_trade_id='t-2',
                qty=Decimal('1'),
                price=Decimal('50020'),
                fee=Decimal('0.001'),
                fee_asset='BTC',
                is_maker=False,
            ),
        ),
    )
    mgr.register_account(_ACCT)
    with caplog.at_level(logging.INFO):
        await mgr.submit_command(
            **{**_CMD_KWARGS, 'reference_price': Decimal('49950')},
        )
        await asyncio.sleep(0.3)

    matching = [
        record
        for record in caplog.records
        if record.msg.startswith('arrival slippage computed:')
    ]
    assert len(matching) == 1
    arrival_slippage_bps = _extract_decimal_arg(matching[0], 2)
    assert arrival_slippage_bps == Decimal('14.01401401401401401401401401')


@pytest.mark.asyncio
async def test_logs_execution_slippage_for_sell_side(
    mgr: ExecutionManager,
    adapter: AsyncMock,
    caplog: pytest.LogCaptureFixture,
) -> None:
    adapter.submit_order.return_value = SubmitResult(
        venue_order_id='venue-2',
        status=OrderStatus.FILLED,
        immediate_fills=(
            ImmediateFill(
                venue_trade_id='t-3',
                qty=Decimal('1'),
                price=Decimal('49980'),
                fee=Decimal('0.001'),
                fee_asset='BTC',
                is_maker=False,
            ),
        ),
    )
    mgr.register_account(_ACCT)
    with caplog.at_level(logging.INFO):
        await mgr.submit_command(
            **{
                **_CMD_KWARGS,
                'side': OrderSide.SELL,
                'reference_price': Decimal('50000'),
            },
        )
        await asyncio.sleep(0.3)

    execution_records = [
        record
        for record in caplog.records
        if record.msg.startswith('execution slippage computed:')
    ]
    arrival_records = [
        record
        for record in caplog.records
        if record.msg.startswith('arrival slippage computed:')
    ]
    assert len(execution_records) == 1
    assert len(arrival_records) == 1
    execution_slippage_bps = _extract_decimal_arg(execution_records[0], 2)
    arrival_slippage_bps = _extract_decimal_arg(arrival_records[0], 2)
    assert execution_slippage_bps == Decimal('-4')
    assert arrival_slippage_bps == Decimal('-4')


def _guard_manager(max_slippage_bps: Decimal | None) -> ExecutionManager:
    return ExecutionManager(
        event_spine=MagicMock(), epoch_id=_EPOCH, venue_adapter=MagicMock(),
        max_slippage_bps=max_slippage_bps,
    )


def _market_command() -> TradeCommand:
    return TradeCommand(command_id='c1', **{**_CMD_KWARGS, 'order_type': OrderType.MARKET})


def _estimate(slippage_bps: str) -> SlippageEstimate:
    return SlippageEstimate(
        mid_price=Decimal('100'), simulated_vwap=Decimal('101'),
        slippage_estimate_bps=Decimal(slippage_bps),
    )


def test_slippage_guard_rejects_market_over_limit() -> None:
    reason = _guard_manager(Decimal('20'))._slippage_guard_reason(
        _market_command(), _estimate('50'),
    )

    assert reason is not None
    assert '50' in reason


def test_slippage_guard_allows_within_limit() -> None:
    assert _guard_manager(Decimal('60'))._slippage_guard_reason(
        _market_command(), _estimate('50'),
    ) is None


def test_slippage_guard_skips_limit_orders() -> None:
    limit_cmd = TradeCommand(command_id='c1', **_CMD_KWARGS)

    assert _guard_manager(Decimal('20'))._slippage_guard_reason(
        limit_cmd, _estimate('50'),
    ) is None


def test_slippage_guard_disabled_when_unset() -> None:
    assert _guard_manager(None)._slippage_guard_reason(
        _market_command(), _estimate('50'),
    ) is None


def test_slippage_guard_fails_closed_on_missing_estimate() -> None:
    reason = _guard_manager(Decimal('20'))._slippage_guard_reason(
        _market_command(), None,
    )

    assert reason is not None
    assert 'usable book depth' in reason


def test_slippage_guard_allows_missing_estimate_when_unset() -> None:
    assert _guard_manager(None)._slippage_guard_reason(
        _market_command(), None,
    ) is None


def test_slippage_guard_skips_limit_orders_on_missing_estimate() -> None:
    limit_cmd = TradeCommand(command_id='c1', **_CMD_KWARGS)

    assert _guard_manager(Decimal('20'))._slippage_guard_reason(
        limit_cmd, None,
    ) is None


def _filled_result(price: Decimal) -> SubmitResult:

    return SubmitResult(
        venue_order_id='venue-1',
        status=OrderStatus.FILLED,
        immediate_fills=(
            ImmediateFill(
                venue_trade_id='t-outcome',
                qty=Decimal('1'),
                price=price,
                fee=Decimal('0.001'),
                fee_asset='BTC',
                is_maker=False,
            ),
        ),
    )


@pytest.mark.asyncio
async def test_outcome_carries_the_slippage_it_logs(
    spine: EventSpine,
    adapter: AsyncMock,
) -> None:
    '''Both measures must reach the outcome, not only the log.

    They were computed per fill and written to two `_log.info` lines and
    nowhere else, so nothing downstream could read what execution had cost:
    not the decision layer, not the Event Spine, not a later analysis of
    the epoch. The values are the same ones the log lines carry.
    '''

    outcomes: list[TradeOutcome] = []

    async def capture(outcome: TradeOutcome) -> None:
        outcomes.append(outcome)

    manager = ExecutionManager(
        event_spine=spine, epoch_id=_EPOCH, venue_adapter=adapter,
        on_trade_outcome=capture,
    )
    adapter.submit_order.return_value = _filled_result(Decimal('50020'))
    manager.register_account(_ACCT)

    await manager.submit_command(
        **{**_CMD_KWARGS, 'reference_price': Decimal('49950')},
    )
    await asyncio.sleep(0.3)

    terminal = [o for o in outcomes if o.is_terminal]

    assert terminal, 'no terminal outcome produced'

    outcome = terminal[-1]

    assert outcome.execution_slippage_bps == Decimal('4')
    assert outcome.arrival_slippage_bps == Decimal(
        '14.01401401401401401401401401',
    )

    await manager.unregister_account(_ACCT)


@pytest.mark.asyncio
async def test_slippage_is_none_when_its_inputs_are_absent(
    spine: EventSpine,
    adapter: AsyncMock,
) -> None:
    '''A measure with no input is absent, not zero.

    Zero is a real reading — it says execution landed on the reference. A
    command that carried no reference price has no arrival measure at all,
    and the two must not be reported as the same thing.
    '''

    outcomes: list[TradeOutcome] = []

    async def capture(outcome: TradeOutcome) -> None:
        outcomes.append(outcome)

    manager = ExecutionManager(
        event_spine=spine, epoch_id=_EPOCH, venue_adapter=adapter,
        on_trade_outcome=capture,
    )
    adapter.submit_order.return_value = _filled_result(Decimal('50020'))
    manager.register_account(_ACCT)

    await manager.submit_command(**_CMD_KWARGS)
    await asyncio.sleep(0.3)

    terminal = [o for o in outcomes if o.is_terminal]

    assert terminal

    assert terminal[-1].arrival_slippage_bps is None
    assert terminal[-1].execution_slippage_bps == Decimal('4')

    await manager.unregister_account(_ACCT)


@pytest.mark.asyncio
async def test_slippage_survives_the_spine(
    spine: EventSpine,
    adapter: AsyncMock,
) -> None:
    '''A replayed outcome must report what the produced one reported.

    The inputs the measures are derived from — the pre-submission estimate
    and the command's reference price — are not on the spine, so an outcome
    rebuilt from the record cannot recompute them. Persisting the measures
    is what keeps a restart from reporting None where the live run
    reported a number.
    '''

    manager = ExecutionManager(
        event_spine=spine, epoch_id=_EPOCH, venue_adapter=adapter,
    )
    adapter.submit_order.return_value = _filled_result(Decimal('50020'))
    manager.register_account(_ACCT)

    await manager.submit_command(
        **{**_CMD_KWARGS, 'reference_price': Decimal('49950')},
    )
    await asyncio.sleep(0.3)

    produced = [
        event for _, event in await spine.read(_EPOCH, after_seq=0)
        if isinstance(event, TradeOutcomeProduced)
    ]

    assert produced

    record = produced[-1]

    assert record.execution_slippage_bps == Decimal('4')
    assert record.arrival_slippage_bps == Decimal(
        '14.01401401401401401401401401',
    )

    rebuilt = _trade_outcome_from_produced(record)

    assert rebuilt.execution_slippage_bps == record.execution_slippage_bps
    assert rebuilt.arrival_slippage_bps == record.arrival_slippage_bps

    await manager.unregister_account(_ACCT)


@pytest.mark.asyncio
async def test_a_sell_below_the_benchmark_reads_negative(
    spine: EventSpine,
    adapter: AsyncMock,
) -> None:
    '''The measures are signed displacement, not side-adjusted cost.

    A SELL filling below its benchmark is the worse outcome and reads
    negative, where a BUY filling below its benchmark is the better one and
    reads the same. A consumer treating the sign as quality would read this
    backwards for one side, so the convention is pinned rather than left to
    be inferred from a BUY-only test.
    '''

    outcomes: list[TradeOutcome] = []

    async def capture(outcome: TradeOutcome) -> None:
        outcomes.append(outcome)

    manager = ExecutionManager(
        event_spine=spine, epoch_id=_EPOCH, venue_adapter=adapter,
        on_trade_outcome=capture,
    )
    adapter.submit_order.return_value = _filled_result(Decimal('49950'))
    manager.register_account(_ACCT)

    await manager.submit_command(
        **{
            **_CMD_KWARGS,
            'side': OrderSide.SELL,
            'reference_price': Decimal('50000'),
        },
    )
    await asyncio.sleep(0.3)

    terminal = [o for o in outcomes if o.is_terminal]

    assert terminal

    arrival = terminal[-1].arrival_slippage_bps

    assert arrival is not None
    assert arrival < Decimal('0'), (
        f'a sell {arrival} bps from its reference should read negative'
    )
    assert arrival == Decimal('-10')

    await manager.unregister_account(_ACCT)


@pytest.mark.asyncio
async def test_arrival_is_measured_when_no_estimate_was_taken(
    spine: EventSpine,
    adapter: AsyncMock,
) -> None:
    '''One measure missing must not suppress the other.

    They have separate inputs: the estimate is a pre-submission book query
    that can fail, the reference price comes with the command. A failed
    query leaves execution slippage absent and arrival slippage intact.
    '''

    outcomes: list[TradeOutcome] = []

    async def capture(outcome: TradeOutcome) -> None:
        outcomes.append(outcome)

    manager = ExecutionManager(
        event_spine=spine, epoch_id=_EPOCH, venue_adapter=adapter,
        on_trade_outcome=capture,
    )
    adapter.query_order_book.side_effect = TransientError('depth unavailable')
    adapter.submit_order.return_value = _filled_result(Decimal('50020'))
    manager.register_account(_ACCT)

    await manager.submit_command(
        **{**_CMD_KWARGS, 'reference_price': Decimal('49950')},
    )
    await asyncio.sleep(0.3)

    terminal = [o for o in outcomes if o.is_terminal]

    assert terminal

    assert terminal[-1].execution_slippage_bps is None
    assert terminal[-1].arrival_slippage_bps == Decimal(
        '14.01401401401401401401401401',
    )

    await manager.unregister_account(_ACCT)
