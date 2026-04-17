# Trading

This page explains the manager-facing runtime façade exposed by Praxis.

## What Trading Is

`praxis/trading.py` composes the execution runtime into one manager-facing object. It owns:

- startup and shutdown of the trading runtime
- account registration through `TradingInbound`
- startup replay from the Event Spine
- Binance user-stream wiring when the Binance adapter is active
- reconciliation against venue state after replay
- outcome routing back to per-account queues

From the rest of the system's point of view, `Trading` is the main execution service object.

## What It Exposes

The main public operations are:

- `start()`
- `stop()`
- `register_account()`
- `unregister_account()`
- `submit_command()`
- `submit_abort()`
- `pull_positions()`

The object also keeps track of:

- registered outcome queues per account
- managed accounts
- user streams
- readiness state after startup and reconciliation

## Startup Model

`Trading.start()`:

1. ensures the Event Spine schema exists
2. reads all events for the current epoch
3. groups those events by account
4. registers each configured account
5. replays each account's event history into the execution manager
6. loads venue filters for active symbols
7. starts the Binance user stream when relevant
8. reconciles the local projection against venue state
9. marks the account ready for new commands

That means new commands are only accepted after replay and reconciliation complete.

## Reconciliation Model

After replay, `Trading` checks open local orders against the venue:

- missing fills are backfilled as `FillReceived`
- terminal venue states become local terminal events
- local projection is updated through the same event-driven path used in live execution

Current reconciliation heals local drift. It does not implement the broader balance-level reconciliation engine described in the RFC.

## Outcome Routing

`TradeOutcome` delivery currently works through in-process async callback production plus per-account queue routing. Each Nexus instance reads from its own `queue.Queue[TradeOutcome]`.

The Event Spine still records `TradeOutcomeProduced`, but it is not yet the sole delivery mechanism described in later post-MMVP design notes.

## Read Next

- [Execution Manager](Execution-Manager.md)
- [Recovery And Reconciliation](Recovery-And-Reconciliation.md)
- [Trade Outcomes](Trade-Outcomes.md)
