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

The schema is versioned by `PRAGMA user_version` and advanced by a transactional, fail-closed-on-newer migration in `EventSpine.ensure_schema`. The shipped version is 3:

- `events(event_seq, epoch_id, timestamp, event_type, payload, prev_hash, hash)`
- index on `(epoch_id, event_seq)`
- `fill_dedup(epoch_id, account_id, dedup_key)` — legacy, bare venue trade id
- `fill_dedup_v2(epoch_id, account_id, symbol, dedup_key)` — per-symbol key
- `reconcile_cursor(account_id, symbol, last_confirmed_trade_id, last_confirmed_ts, epoch_id, updated_at)` — durable myTrades cursor, keyed on `(account_id, symbol)`, outlives epochs
- `spine_meta(key, value)` — chain version, genesis anchor, and the one proven legacy dedup symbol

The `prev_hash`/`hash` columns hold a SHA-256 chain over a length-framed preimage (domain marker, chain version, predecessor hash, `event_seq`, `epoch_id`, timestamp, event type, payload), computed per append under the same lock. Legacy rows written before the chain keep a NULL-hash prefix and are not backfilled.

`fill_dedup_v2` prevents the same fill from being counted twice, per symbol, when venue reconnection or reconciliation replays old fills. `FillReceived` dedup dual-reads the legacy `fill_dedup` table only for the single symbol proven present before migration; the version 3 migration fails closed if the legacy table spans more than one symbol or holds an unmatched row.

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
