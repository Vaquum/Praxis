# Praxis Infrastructure

This package contains the persistence and venue-integration layer for Praxis.

## What This Package Owns

- Event Spine persistence
- venue adapter protocol and Binance implementation
- Binance URL configuration
- Binance user-stream integration
- observability helpers and runtime transport surfaces

## What It Does Not Own

- high-level execution orchestration in `Trading`
- the `ExecutionManager` command lifecycle
- canonical public docs outside this module boundary

## Key Entry Points

- `praxis/infrastructure/event_spine.py`
- `praxis/infrastructure/venue_adapter.py`
- `praxis/infrastructure/binance_adapter.py`
- `praxis/infrastructure/binance_ws.py`
- `praxis/infrastructure/binance_urls.py`

## Read Next

- [Event Spine](../../docs/Event-Spine.md)
- [Venue Adapter](../../docs/Venue-Adapter.md)
- [Binance Spot Testnet](../../docs/Binance-Spot-Testnet.md)
