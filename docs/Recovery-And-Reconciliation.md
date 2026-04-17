# Recovery And Reconciliation

This page explains how Praxis rebuilds state after startup and how it heals local drift against the venue.

## Startup Recovery

Praxis recovery starts from the Event Spine, not from mutable in-memory state.

The current startup path is:

1. read all events for the current epoch
2. replay those events per account into `TradingState`
3. load symbol filters for any active symbols
4. reconnect Binance user streams
5. reconcile open local orders against the venue
6. mark accounts ready only after replay and reconciliation

That means a process restart can rebuild local order and position state deterministically from durable events.

## What Reconciliation Does

The current implementation focuses on execution-state reconciliation:

- query open orders from the venue
- query trades for orders whose filled quantity is ahead on the venue
- backfill missing `FillReceived` events
- backfill terminal order states when the venue is already canceled, expired, or rejected

Reconciliation uses event append plus normal projection updates, rather than mutating local state out of band.

## What It Does Not Yet Do

The RFC describes a broader reconciliation engine than what ships today. The current code does not yet implement:

- full balance-level reconciliation across all assets
- the richer mismatch reporting surface described in the RFC
- a system-wide health/reduce-only/halt response inside Praxis itself

So the right way to describe the current behavior is: recovery and order-level reconciliation are implemented; the full RFC reconciliation engine is not.

## Why Fill Dedup Matters

Praxis uses `fill_dedup` in the Event Spine to avoid double-counting fills during:

- WebSocket reconnection
- REST backfill
- reconciliation after restart

Without that dedup path, repeated venue fills could inflate positions and distort outcomes.

## Read Next

- [Event Spine](Event-Spine.md)
- [Trading State](Trading-State.md)
- [Binance Spot Testnet](Binance-Spot-Testnet.md)
