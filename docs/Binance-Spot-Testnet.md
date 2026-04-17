# Binance Spot Testnet

This page explains the current venue target for Praxis and what that means operationally.

## What Praxis Uses Today

Praxis currently targets Binance Spot testnet for the paper-trading path.

The main constants live in:

- `praxis/infrastructure/binance_urls.py`
- `tests/testnet/conftest.py`

The testnet URLs are:

- REST: `https://testnet.binance.vision`
- WebSocket: `wss://stream.testnet.binance.vision`

## Why Testnet Matters

The current repository is designed around paper trading first:

- same general API shape as Binance Spot
- no real funds
- safe place to validate command routing, fills, replay, and recovery

This is the execution environment the tests and docs are written around.

## What Carries Over To Mainnet

Most core execution logic is shared:

- signing
- order normalization
- execution report parsing
- filter loading
- order-book queries
- replay and reconciliation logic

The main change between testnet and mainnet is URL and credential configuration, not a different execution architecture.

## Testnet Caveats

Testnet does not behave like production liquidity:

- books are thinner and synthetic
- fill behavior can be less realistic
- resets can wipe data
- network availability can vary

So testnet is good for exercising the execution engine, but it is not a realistic substitute for production slippage, latency, or liquidity conditions.

## Read Next

- [Setup And Verification](Setup-And-Verification.md)
- [Venue Adapter](Venue-Adapter.md)
- [Recovery And Reconciliation](Recovery-And-Reconciliation.md)
