'''
Represent core projection and domain types for the Praxis Trading sub-system.

Re-exports TradingState and ExecutionManager from the core package.
'''

from __future__ import annotations

from praxis.core.execution_manager import AccountNotRegisteredError, ExecutionManager
from praxis.core.trading_state import TradingState

__all__ = ['AccountNotRegisteredError', 'ExecutionManager', 'TradingState']
