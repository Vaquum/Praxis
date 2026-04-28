'''Integration test for PT-FIX-7: launcher's PraxisOutbound translates
Nexus-shape `execution_params` into `SingleShotParams` before reaching
`Trading.submit_command`.

The launcher wraps `trading.submit_command` inside
`_build_praxis_outbound` so that a Nexus `TradeCommand.execution_params`
of `None` or `Mapping[str, object]` becomes a valid `SingleShotParams`
on the Praxis side. Without this, `Trading.submit_command`'s
`isinstance(execution_params, SingleShotParams)` enforcement raises
`TypeError` on every order.
'''

from __future__ import annotations

import asyncio
import threading
from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

from praxis.core.domain.enums import (
    ExecutionMode,
    MakerPreference,
    OrderSide,
    OrderType,
    STPMode,
)
from praxis.core.domain.single_shot_params import SingleShotParams
from praxis.launcher import _build_praxis_outbound


def _build_outbound() -> tuple[MagicMock, asyncio.AbstractEventLoop, threading.Thread, object]:
    trading = MagicMock()
    trading.submit_command = AsyncMock(return_value='cmd-id-1')
    trading.register_account = MagicMock()
    trading.unregister_account = AsyncMock()
    trading.pull_positions = MagicMock(return_value={})

    def _submit_abort(_abort: object) -> None:
        return None

    trading.submit_abort = MagicMock(side_effect=_submit_abort)
    trading.get_health_snapshot = AsyncMock()

    loop = asyncio.new_event_loop()
    loop_thread = threading.Thread(target=loop.run_forever, daemon=True)
    loop_thread.start()

    outbound = _build_praxis_outbound(trading, loop)

    return trading, loop, loop_thread, outbound


def _build_command(execution_params: object) -> MagicMock:
    command = MagicMock()
    command.command_id = 'nexus-cmd-1'
    command.trade_id = 'trade-1'
    command.account_id = 'acct-1'
    command.symbol = 'BTCUSDT'
    command.side = OrderSide.BUY
    command.size = Decimal('0.1')
    command.order_type = OrderType.MARKET
    command.execution_mode = ExecutionMode.SINGLE_SHOT
    command.execution_params = execution_params
    command.deadline = 30
    command.reference_price = None
    command.maker_preference = MakerPreference.NO_PREFERENCE
    command.stp_mode = STPMode.NONE
    command.created_at = datetime.now(UTC)
    return command


def _stop_loop(loop: asyncio.AbstractEventLoop, thread: threading.Thread) -> None:
    loop.call_soon_threadsafe(loop.stop)
    thread.join(timeout=5)
    if not loop.is_closed():
        loop.close()


def test_send_command_translates_none_to_default_single_shot_params() -> None:

    trading, loop, thread, outbound = _build_outbound()

    try:
        outbound.send_command(_build_command(execution_params=None))
    finally:
        _stop_loop(loop, thread)

    trading.submit_command.assert_called_once()
    forwarded = trading.submit_command.call_args.kwargs['execution_params']
    assert isinstance(forwarded, SingleShotParams)
    assert forwarded.price is None


def test_send_command_translates_mapping_to_single_shot_params() -> None:

    trading, loop, thread, outbound = _build_outbound()

    try:
        outbound.send_command(
            _build_command(execution_params={'price': Decimal('100')}),
        )
    finally:
        _stop_loop(loop, thread)

    forwarded = trading.submit_command.call_args.kwargs['execution_params']
    assert isinstance(forwarded, SingleShotParams)
    assert forwarded.price == Decimal('100')


def test_send_command_passes_through_pre_built_single_shot_params() -> None:

    trading, loop, thread, outbound = _build_outbound()
    sentinel = SingleShotParams(price=Decimal('200'))

    try:
        outbound.send_command(_build_command(execution_params=sentinel))
    finally:
        _stop_loop(loop, thread)

    forwarded = trading.submit_command.call_args.kwargs['execution_params']
    assert forwarded is sentinel
