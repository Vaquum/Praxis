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

The schema is versioned by `PRAGMA user_version` and advanced by a transactional, fail-closed-on-newer migration in `EventSpine.ensure_schema`. Each migration is gated on the version that introduced it, so a database already past one does not re-run it. The shipped version is 4:

- `events(event_seq, epoch_id, timestamp, event_type, payload, prev_hash, hash)`
- index on `(epoch_id, event_seq)`
- `fill_dedup_v2(epoch_id, account_id, symbol, dedup_key)` — per-symbol key
- `reconcile_cursor(account_id, symbol, last_confirmed_trade_id, last_confirmed_ts, epoch_id, updated_at)` — durable myTrades cursor, keyed on `(account_id, symbol)`, outlives epochs
- `spine_meta(key, value)` — chain version, genesis anchor, and the one proven legacy dedup symbol

The `prev_hash`/`hash` columns hold a SHA-256 chain over a length-framed preimage (domain marker, chain version, predecessor hash, `event_seq`, `epoch_id`, timestamp, event type, payload), computed per append under the same lock. Legacy rows written before the chain keep a NULL-hash prefix and are not backfilled.

Because the chain version and the genesis anchor are both mixed into every hash, a database recording different ones holds a chain in another dialect — one this build can neither extend honestly nor verify. Schema v1 and later must retain both identity keys and the `spine_meta` table. `ensure_schema` checks them against this build before any schema writes, including table creation, and refuses missing or incompatible identity without recreating it. Only an unversioned database (`user_version = 0`) may initialize identity, including resuming interrupted initialization; that identity is checked before the dedup migrations. A versioned database that lost identity requires operator investigation, not automatic reseeding.

`fill_dedup_v2` prevents the same fill from being counted twice, per symbol, when venue reconnection or reconciliation replays old fills. The version 3 migration proved the single symbol the legacy `fill_dedup` table held, failing closed if it spanned more than one symbol or held an unmatched row; the version 4 migration replays those rows into `fill_dedup_v2` under that proven symbol and drops the legacy table, so dedup now has one home and an append performs one read rather than two. The fold confirms each key present in `fill_dedup_v2` before dropping anything, key by key rather than by count, and is written to be resumed rather than rolled back — an interrupted migration completes on the next open.

## What It Guarantees

The Event Spine provides:

- monotonically ordered events per epoch
- durable persistence in SQLite
- event hydration back into typed dataclasses
- a tamper-evident hash chain verified at boot by `verify_chain` before order capability, failing closed on a broken link, altered field, deletion, or a hashed-to-unhashed transition
- per-symbol duplicate-fill suppression for `FillReceived`
- a durable per-`(account, symbol)` reconcile cursor for myTrades backfill
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
