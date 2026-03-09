'''
Represent core projection and domain types for the Praxis Trading sub-system.

Re-exports TradingState, ExecutionManager, and generate_client_order_id from the core package.
'''

from __future__ import annotations

from praxis.core.execution_manager import AccountNotRegisteredError, ExecutionManager
from praxis.core.trading_state import TradingState
from praxis.core.generate_client_order_id import generate_client_order_id

__all__ = [
    'AccountNotRegisteredError',
    'ExecutionManager',
    'TradingState',
    'generate_client_order_id',
]
