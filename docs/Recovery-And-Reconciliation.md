# Recovery And Reconciliation

This page explains how Praxis rebuilds state after startup and how it heals local drift against the venue.

## Startup Recovery

Praxis recovery starts from the Event Spine, not from mutable in-memory state.

The current startup path is:

1. read all events for the current epoch
2. verify the Event Spine hash chain before granting order capability
3. replay those events per account into `TradingState`
4. load symbol filters for any active symbols
5. connect Binance user streams
6. backfill missed fills from the reconcile cursor and reconcile open local orders against the venue while submission is gated
7. mark accounts ready only after replay and a complete reconciliation

That means a process restart can rebuild local order and position state deterministically from durable events.

## What Reconciliation Does

The current implementation focuses on execution-state reconciliation:

- query open orders from the venue
- walk myTrades from the durable per-`(account, symbol)` reconcile cursor (inclusive overlap, exclusive advance, short-page stop, per-pass page cap), or from a bootstrap time window when no cursor exists yet
- backfill missing `FillReceived` events and advance the cursor after each append
- backfill terminal order states when the venue is already canceled, expired, or rejected

Reconciliation uses event append plus normal projection updates, rather than mutating local state out of band.

## The Reconnect Submission Gate

Reconnect reconciliation runs at boot and on every WebSocket reconnect edge. While it runs, new-command submission for that account is gated so no order is sent against a local view that has not yet absorbed the missed fills. The account is released only after a complete backfill and reconcile.

The gate is fail-closed:

- an incomplete backfill (page cap hit) keeps the account gated until a later pass drains the remainder
- a venue failure keeps the account gated
- a projection failure poisons the account: the per-account writer stops projecting and the account trades no further until a restart replays the durable state

Re-entering reconciliation while a pass is already in flight schedules exactly one rerun, so a reconnect that arrives mid-reconcile is not lost.

## What It Does Not Yet Do

The RFC describes a broader reconciliation engine than what ships today. The current code does not yet implement:

- full balance-level reconciliation across all assets
- the richer mismatch reporting surface described in the RFC
- a system-wide health/reduce-only/halt response inside Praxis itself

So the right way to describe the current behavior is: recovery and order-level reconciliation are implemented; the full RFC reconciliation engine is not.

## Why Fill Dedup Matters

Praxis uses `fill_dedup_v2` in the Event Spine — keyed per `(epoch, account, symbol, venue_trade_id)` — to avoid double-counting fills during:

- WebSocket reconnection
- REST backfill
- reconciliation after restart

Without that dedup path, repeated venue fills could inflate positions and distort outcomes. The legacy `fill_dedup` table is dual-read only for the one symbol proven present before the version 3 migration.

## Read Next

- [Event Spine](Event-Spine.md)
- [Trading State](Trading-State.md)
- [Binance Spot Testnet](Binance-Spot-Testnet.md)
