'''
TradeCommand intake with per-account queues and backpressure.

Route commands to per-account coroutines via bounded asyncio queues.
Each registered account owns an independent command queue, priority
queue, and asyncio task.
'''

from __future__ import annotations

import asyncio
import logging

from praxis.core.domain.trade_abort import TradeAbort
from praxis.core.domain.trade_command import TradeCommand
from praxis.core.trading_state import TradingState
from praxis.infrastructure.event_spine import EventSpine

__all__ = ['AccountNotRegisteredError', 'CommandQueueFullError', 'ExecutionManager']

_log = logging.getLogger(__name__)

_DEFAULT_MAX_QUEUE_DEPTH = 100


class AccountNotRegisteredError(Exception):
    '''Raised when a command targets an unregistered account_id.'''


class CommandQueueFullError(Exception):
    '''Raised when the per-account command queue has no capacity.'''


class _AccountRuntime:
    '''
    Per-account runtime state owned by ExecutionManager.

    Args:
        account_id (str): Account identifier.
        command_queue (asyncio.Queue[TradeCommand]): Bounded queue for commands.
        priority_queue (asyncio.Queue[TradeAbort]): Unbounded queue for aborts.
        trading_state (TradingState): Per-account state projection.
    '''

    def __init__(
        self,
        account_id: str,
        command_queue: asyncio.Queue[TradeCommand],
        priority_queue: asyncio.Queue[TradeAbort],
        trading_state: TradingState,
    ) -> None:
        '''
        Store per-account queues and projection.

        Args:
            account_id (str): Account identifier.
            command_queue (asyncio.Queue[TradeCommand]): Bounded queue for commands.
            priority_queue (asyncio.Queue[TradeAbort]): Unbounded queue for aborts.
            trading_state (TradingState): Per-account state projection.
        '''

        self.account_id = account_id
        self.command_queue = command_queue
        self.priority_queue = priority_queue
        self.trading_state = trading_state
        self.task: asyncio.Task[None] | None = None


class ExecutionManager:
    '''
    Orchestrate TradeCommand intake and per-account queue routing.

    Args:
        event_spine (EventSpine): Append-only event log for persistence.
        epoch_id (int): Current epoch identifier.
        max_queue_depth (int): Per-account command queue bound.
    '''

    def __init__(
        self,
        event_spine: EventSpine,
        epoch_id: int,
        max_queue_depth: int = _DEFAULT_MAX_QUEUE_DEPTH,
    ) -> None:
        '''
        Store dependencies and initialize empty account registry.

        Args:
            event_spine (EventSpine): Append-only event log for persistence.
            epoch_id (int): Current epoch identifier.
            max_queue_depth (int): Per-account command queue bound.
        '''

        if max_queue_depth <= 0:
            msg = 'ExecutionManager.max_queue_depth must be positive'
            raise ValueError(msg)

        self._event_spine = event_spine
        self._epoch_id = epoch_id
        self._max_queue_depth = max_queue_depth
        self._accounts: dict[str, _AccountRuntime] = {}
