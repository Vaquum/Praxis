# Execution Manager

This page explains the runtime core that turns commands into orders, fills, positions, and outcomes.

## What The Execution Manager Is

`praxis/core/execution_manager.py` is the orchestration core for the Trading sub-system. It owns:

- per-account runtimes
- per-account command queues
- abort queues
- WebSocket event queues
- command-to-trade and command-to-order tracking
- `TradingState` projection per account

## Account Isolation

Each registered account gets its own `_AccountRuntime`:

- `command_queue`
- `priority_queue` for aborts
- `ws_event_queue`
- `TradingState`
- task running the account loop

That is the main runtime mechanism behind Praxis multi-account isolation.

## Command Flow

When a command is submitted:

1. it is validated
2. it is routed to the correct account queue
3. the account loop processes it
4. slippage estimate is attempted from the order book
5. `OrderSubmitIntent` is appended before the venue call
6. venue submission happens
7. order, fill, and outcome events are appended and projected

The persist-before-send intent event is one of the key recovery protections in the current implementation.

## WebSocket Event Flow

Venue execution reports are normalized into domain events and enqueued back onto the account runtime. Those events update local state through the same event-driven path rather than bypassing it.

This matters because fill and terminal events must stay consistent with replay logic and dedup behavior.

## Aborts

`ExecutionManager.submit_abort()` queues abort requests for an existing command. Abort handling cancels live venue orders, computes the actual filled result, and produces a terminal outcome that reflects what was really executed.

## Current Scope

The current runtime executes `SINGLE_SHOT` commands end to end. Unsupported execution modes are rejected with a clear terminal result rather than silently doing partial work.

## Read Next

- [Trade Lifecycle](Trade-Lifecycle.md)
- [Event Spine](Event-Spine.md)
- [Trading State](Trading-State.md)
