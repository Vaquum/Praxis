# Praxis Core

This package contains the execution-state core for Praxis.

## What This Package Owns

- `ExecutionManager`
- `TradingState`
- command and abort validation
- deterministic client order id generation
- slippage estimation
- the domain model used by the execution layer

## What It Does Not Own

- top-level runtime orchestration in `praxis/trading.py`
- venue transport and exchange integration in `praxis/infrastructure`
- canonical public docs outside this module boundary

## Key Entry Points

- `praxis/core/execution_manager.py`
- `praxis/core/trading_state.py`
- `praxis/core/estimate_slippage.py`
- `praxis/core/validate_trade_command.py`
- `praxis/core/validate_trade_abort.py`
- `praxis/core/domain`

## Read Next

- [Execution Manager](../../docs/Execution-Manager.md)
- [Trading State](../../docs/Trading-State.md)
- [Trade Lifecycle](../../docs/Trade-Lifecycle.md)
