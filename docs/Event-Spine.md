# Event Spine

This page explains the current durable event log used by Praxis.

## What The Event Spine Is

`praxis/infrastructure/event_spine.py` is the SQLite-backed append-only event log for the Trading sub-system. It is the durable source of truth for order and fill facts that matter to recovery.

Today it stores:

- `CommandAccepted`
- `OrderSubmitIntent`
- `OrderSubmitted`
- `OrderSubmitFailed`
- `OrderAcked`
- `FillReceived`
- `OrderRejected`
- `OrderCanceled`
- `OrderExpired`
- `TradeClosed`
- `TradeOutcomeProduced`

## Current Schema

The shipped schema is intentionally small:

- `events(event_seq, epoch_id, timestamp, event_type, payload)`
- index on `(epoch_id, event_seq)`
- `fill_dedup(epoch_id, account_id, dedup_key)`

`fill_dedup` prevents the same fill from being counted twice when venue reconnection or reconciliation replays old fills.

## What It Guarantees

The Event Spine provides:

- monotonically ordered events per epoch
- durable persistence in SQLite
- event hydration back into typed dataclasses
- duplicate-fill suppression for `FillReceived`
- replay support on startup

That is enough for the current replay model:

1. read all events for the current epoch
2. group them by account
3. replay them into `TradingState`
4. reconcile the rebuilt local view against the venue

## What It Does Not Yet Provide

The RFC and post-MMVP notes describe a broader spine contract than what is currently shipped. In particular, the current implementation does not yet provide:

- cursor-based subscriber delivery
- push subscription from spine append to downstream consumers
- the broader multi-consumer outbox/cursor model described in later design notes
- full cross-subsystem event delivery guarantees for Nexus

Those are future design directions, not current behavior.

## Why It Matters

Without the Event Spine, Praxis would need to trust mutable in-memory state at crash time. With it, `TradingState` is always rebuildable from durable facts.

## Read Next

- [Trading State](Trading-State.md)
- [Execution Manager](Execution-Manager.md)
- [Launcher](Launcher.md)
