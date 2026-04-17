# Praxis Package

This package is the top-level execution façade for Praxis.

## What This Package Owns

- public package exports for the trading runtime
- top-level runtime composition through `Trading`
- runtime configuration through `TradingConfig`
- launcher, market data poller, and manager-facing inbound surfaces

## What It Does Not Own

- detailed domain rules and projection logic, which live under `praxis/core`
- venue-specific protocol and exchange integration, which live under `praxis/infrastructure`
- canonical public docs, which live under `/docs`

## Key Entry Points

- `praxis/trading.py`
- `praxis/trading_config.py`
- `praxis/trading_inbound.py`
- `praxis/launcher.py`
- `praxis/market_data_poller.py`

## Adjacent Modules

- `praxis/core`
- `praxis/infrastructure`

## Read Next

- [Product Home](../README.md)
- [Praxis Docs Hub](../docs/README.md)
- [Trading](../docs/Trading.md)
