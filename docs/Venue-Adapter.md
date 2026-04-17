# Venue Adapter

This page explains the exchange boundary used by Praxis and the current Binance Spot implementation.

## What The Venue Adapter Is

`praxis/infrastructure/venue_adapter.py` defines the venue-agnostic protocol used by the execution layer. It exists so `ExecutionManager` and `Trading` can work with normalized exchange types rather than raw Binance payloads.

The protocol covers:

- order submission and cancellation
- order, trade, balance, and order-book queries
- symbol filter loading
- execution report normalization

## Current Implementation

The shipped concrete implementation is `BinanceAdapter` in `praxis/infrastructure/binance_adapter.py`.

It handles:

- REST authentication and signing
- per-account API key and secret storage
- filter loading for symbols
- request retries for transient failures
- normalization of Binance statuses and execution types into internal enums
- public and authenticated query surfaces
- Spot testnet and mainnet URL selection

## Why Filters Matter

Praxis loads Binance symbol filters so it can reject invalid orders before spending a venue round-trip. The current code tracks:

- tick size
- lot step
- lot minimum and maximum
- minimum notional

That shapes what order quantities and prices are legal for a given symbol.

## Testnet Boundary

The current paper-trading path uses Binance Spot testnet URLs. The adapter is designed so testnet versus mainnet is primarily a configuration change, not a different execution model. That said, the repository and tests are currently centered on testnet behavior.

## Order Book And Slippage

The adapter also exposes order-book snapshots. Praxis uses those snapshots for walk-the-book slippage estimation before submission.

## Current Boundary

The adapter abstracts the venue boundary, but the current repository is not yet a generalized multi-venue platform. Binance Spot is the real shipped target.

## Read Next

- [Execution Manager](Execution-Manager.md)
- [Trade Lifecycle](Trade-Lifecycle.md)
- [Setup And Verification](Setup-And-Verification.md)
