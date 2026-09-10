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

`ExecutionManager.submit_abort()` queues abort requests for an existing command, and `ExecutionManager.submit_modify()` queues an order-price / scheme-plan amend ahead of new commands on the account writer. Abort handling cancels live venue orders, computes the actual filled result, and produces a terminal outcome that reflects what was really executed.

If a ladder is mid-amend, abort retires and venue-confirms both its old and any already-submitted replacement rungs, backfills their fills, and emits one canceled outcome without placing further rungs. An uncertain cancellation remains pending for the watchdog; changing a protection hold to a terminalizing hold never permits replacement placement. An abort not yet durably terminalized still has the existing restart limitation described in [TD-127](TechnicalDebt.md).

## Migration From v0.96.0 To v0.97.0

The interval-slicing modes retain their distinct execution modes but share parameter types. Update imports from `praxis.core.domain` or the corresponding modules:

| Previous public type | Replacement public type | Module |
| --- | --- | --- |
| `TwapParams` | `IntervalSliceParams` | `praxis.core.domain.interval_slice_params` |
| `TimeDcaParams` | `IntervalSliceParams` | `praxis.core.domain.interval_slice_params` |
| `TwapModify` | `IntervalSliceModify` | `praxis.core.domain.interval_slice_modify` |
| `TimeDcaModify` | `IntervalSliceModify` | `praxis.core.domain.interval_slice_modify` |

The old names and modules have no compatibility aliases. Both `TWAP` and `TIME_DCA` now accept `num_slices` and `interval_seconds` in `execution_params`. Rename TIME_DCA's `num_iterations` to `num_slices` in both command and modify payloads; the old key is rejected. TWAP's payload keys do not change.

`IntervalSliceParams` requires integer `num_slices >= 2` and integer `interval_seconds > 0`, excluding booleans. `IntervalSliceModify` accepts the same bounds for each supplied field, permits omitted fields as `None`, and requires at least one field. An amend applies only to the unfilled remainder. `TIME_DCA` remains BUY-only; `TWAP` permits BUY and SELL. Existing persisted `SchemeInitialized` events already use `slices_total`, so the rename does not require rewriting the event history.

The boot-only `drain_ws_events(account_id)` method is now `drain_external_events(account_id)`, covering admission, legacy WebSocket, and dispatch queues while the account writer is parked. `has_pending_ws_events(account_id)` is now `has_pending_external_events(account_id)` and includes an admission currently being appended/projected.

`TradeOutcome` no longer accepts or exposes `missed_iterations` or `missed_reason`; remove them from constructors and consumers, as described in [Trade Outcomes](Trade-Outcomes.md). Back up the event database before opening it with this release: schema 4 drops the legacy dedup table after migrating its keys, and an older build refuses the upgraded database. See [Event Spine](Event-Spine.md).

## Current Scope

The runtime executes every enabled execution mode end to end — `SINGLE_SHOT`, `TWAP`, `TIME_DCA`, `SCHEDULED_VWAP`, `BRACKET`, `ICEBERG`, and `LADDER_DCA` — plus amends of a resting single order, a running scheme, a bracket protective OCO, and a ladder grid. A mode not enabled for the deployment (`enabled_execution_modes`) is rejected with a clear terminal result rather than silently doing partial work. The priority queue carries both aborts and modifies.

Boot replay restores amendable bracket protection for a confirmed `OPEN` OCO. A `PARTIALLY_FILLED` protective OCO is not restored to the live bracket registry, so its remaining protection cannot be amended after restart; this pre-existing limit is tracked as [TD-152](TechnicalDebt.md).

## Read Next

- [Trade Lifecycle](Trade-Lifecycle.md)
- [Event Spine](Event-Spine.md)
- [Trading State](Trading-State.md)
