'''
Represent core projection and domain types for the Praxis Trading sub-system.

Re-exports TradingState, ExecutionManager, generate_client_order_id,
validate_trade_command, and validate_trade_abort from the core package.
'''

from __future__ import annotations

from praxis.core.execution_manager import AccountNotRegisteredError, ExecutionManager
from praxis.core.estimate_slippage import SlippageEstimate, estimate_slippage
from praxis.core.trading_state import TradingState
from praxis.core.generate_client_order_id import generate_client_order_id
from praxis.core.validate_trade_command import validate_trade_command
from praxis.core.validate_trade_abort import validate_trade_abort

__all__ = [
    'AccountNotRegisteredError',
    'ExecutionManager',
    'SlippageEstimate',
    'TradingState',
    'estimate_slippage',
    'generate_client_order_id',
    'validate_trade_abort',
    'validate_trade_command',
]
