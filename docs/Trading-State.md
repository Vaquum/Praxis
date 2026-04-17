# Trading State

This page explains the in-memory execution projection that Praxis rebuilds from the Event Spine.

## What Trading State Is

`praxis/core/trading_state.py` is the per-account projection of orders, positions, and terminal history. It is not an independent store. It is a derived view rebuilt by applying events in sequence.

Each account runtime owns one `TradingState`.

## What It Tracks

The current projection maintains:

- `positions`: keyed by `(trade_id, account_id)`
- `orders`: active orders keyed by `client_order_id`
- `closed_orders`: terminal orders moved out of active tracking
- `trade_strategy_ids`: strategy attribution keyed by `trade_id`

## How It Evolves

The projection is updated through `TradingState.apply(event)`.

Important behaviors:

- `OrderSubmitIntent` creates an order in `SUBMITTING`
- `OrderSubmitted` or `OrderAcked` attaches venue order id and moves toward `OPEN`
- `FillReceived` updates both the order and the position
- terminal order events move orders into `closed_orders`

## Position Semantics

Positions are keyed by trade rather than by symbol netting alone. That means Praxis can preserve trade-level attribution and strategy ownership.

Current fill behavior:

- same-side fills increase position quantity and recompute weighted average entry
- opposite-side fills reduce position quantity
- position quantity is clamped at zero if a reduction would otherwise go negative

## Relation To Reconciliation

`TradingState` is the local view used during reconciliation. Praxis compares the projected local state with venue state and backfills missing fills or terminal statuses when needed.

## Current Boundary

The RFC describes a broader world with an Account sub-system and richer accounting projections. The current `TradingState` is narrower: it is an execution-state projection for orders and positions, not a full accounting ledger.

## Read Next

- [Event Spine](Event-Spine.md)
- [Trade Lifecycle](Trade-Lifecycle.md)
- [Execution Manager](Execution-Manager.md)
