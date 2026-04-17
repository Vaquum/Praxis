# Praxis Core Domain

This package contains the domain types for the Praxis Trading sub-system.

## What This Package Owns

- enums for order, execution, and trade status
- command and abort dataclasses
- order, fill, position, and outcome dataclasses
- domain events projected through the Event Spine

## What It Does Not Own

- queueing and orchestration logic
- venue transport details
- runtime startup and reconciliation control flow

## Key Entry Points

- `praxis/core/domain/enums.py`
- `praxis/core/domain/trade_command.py`
- `praxis/core/domain/trade_abort.py`
- `praxis/core/domain/trade_outcome.py`
- `praxis/core/domain/events.py`

## Read Next

- [Trade Lifecycle](../../../docs/Trade-Lifecycle.md)
- [Trade Outcomes](../../../docs/Trade-Outcomes.md)
- [Event Spine](../../../docs/Event-Spine.md)
