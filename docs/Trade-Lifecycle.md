# Trade Lifecycle

This page explains what happens to a trade after Nexus decides to act.

## What Enters Praxis

Praxis receives trade requests through `Trading.submit_command()` and `TradingInbound.submit_command()`. The command carries:

- `trade_id`
- `account_id`
- `symbol`
- `side`
- `qty`
- `order_type`
- `execution_mode`
- execution parameters such as `SingleShotParams`
- `timeout`
- optional `reference_price`
- maker preference and self-trade-prevention mode
- optional `strategy_id` for position attribution

The code currently ships end-to-end runtime support for `SINGLE_SHOT`. Additional execution modes exist in the domain model and validation layer, but unsupported modes are rejected at execution time.

## Lifecycle Stages

At a high level, the current happy path is:

1. command accepted into the per-account execution queue
2. slippage estimate computed from the order book when available
3. `OrderSubmitIntent` appended before venue submission
4. order submitted to venue
5. `OrderSubmitted` and optional inline `FillReceived` events appended
6. WebSocket execution reports produce later fills or terminal order events
7. `TradeClosed` emitted when the trade becomes terminal with fills
8. `TradeOutcomeProduced` emitted and routed back to Nexus

The event sequence is not just audit data. It is what makes replay and recovery possible.

## Order States

Order states are tracked through `OrderStatus`:

- `SUBMITTING`
- `OPEN`
- `PARTIALLY_FILLED`
- `FILLED`
- `CANCELED`
- `REJECTED`
- `EXPIRED`

The current implementation creates the order in `SUBMITTING` when `OrderSubmitIntent` is projected, promotes it on venue submission or ack, updates filled quantity on each fill, and closes terminal orders into `closed_orders`.

## Outcomes

Praxis produces `TradeOutcome` objects for Nexus. Those outcomes describe what actually happened, not just what the strategy asked for. The outcome path is currently callback-driven in-process, with the event spine retaining the same information for replay and audit.

## Aborts And Expiry

Praxis supports abort handling through `TradeAbort`:

- Nexus or another caller submits an abort
- open venue orders are canceled
- filled quantity is preserved
- outcome reflects actual fills versus intended target

Expiry is enforced from the command timeout. If the deadline is exceeded, Praxis produces an expired terminal result rather than letting the command run forever.

## Current Boundary

The deck and RFC discuss a broader execution-mode surface. The current code does not yet execute TWAP, VWAP, bracket, iceberg, or DCA modes end to end. Those remain future work despite their presence in enums and validation logic.

## Read Next

- [Execution Manager](Execution-Manager.md)
- [Trading State](Trading-State.md)
- [Venue Adapter](Venue-Adapter.md)
