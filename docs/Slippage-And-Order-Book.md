# Slippage And Order Book

This page explains the current slippage estimation path in Praxis.

## What Praxis Computes

Before submission, the execution path attempts a walk-the-book estimate using the current order book.

The current implementation:

- queries the venue order book
- simulates filling the requested quantity through book depth
- computes a simulated VWAP
- compares that VWAP against the mid-price
- logs the resulting slippage estimate

This logic lives in `praxis/core/estimate_slippage.py` and is used by `ExecutionManager`.

## Why It Exists

Praxis is not just trying to route orders. It also wants to preserve execution context that matters downstream:

- expected market impact before submission
- actual fill behavior after submission
- difference between expectation and realized execution

The detailed pipeline deck treats this as part of the execution analytics surface.

## Current Scope

The current shipped implementation gives you:

- pre-trade slippage estimate from the book
- actual fill data in outcomes and state
- the raw ingredients for execution and arrival slippage analysis

It does not yet provide a full standalone analytics subsystem around those values inside the docs or API surface.

## Technical Debt

Current known debt is documented in [TechnicalDebt.md](TechnicalDebt.md):

- slippage estimation scales linearly with book depth

For current depth sizes, that is acceptable. If depth grows substantially, the implementation will need a more efficient Decimal-safe approach.

## Read Next

- [Venue Adapter](Venue-Adapter.md)
- [Execution Manager](Execution-Manager.md)
- [Trade Outcomes](Trade-Outcomes.md)
