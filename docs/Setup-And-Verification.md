# Setup And Verification

This guide covers the fastest honest path to getting Praxis running locally today.

## What This Guide Covers

- cloning the repository
- installing Praxis in editable mode
- running the default test suite
- optionally running Binance Spot testnet verification

## Prerequisites

- Python `>=3.10`
- Node `22` (LTS) recommended; Node `>=20` supported if you also want to build the docs site
- either `uv` or `pip` for the Python install path

## Current Scope

This guide reflects the current Praxis repository, not the full RFC-4001 target system. Today the shipped center of gravity is the Trading sub-system: Binance Spot testnet execution, event-backed state replay, per-account isolation, and integration wiring with Nexus.

## Local Setup

```bash
git clone https://github.com/Vaquum/Praxis.git
cd Praxis
```

If you use `uv`:

```bash
uv pip install -e ".[dev]"
uv run pytest
```

If you use `pip`:

```bash
pip install -e ".[dev]"
python -m pytest
```

The default test suite excludes `tests/testnet` through `pyproject.toml`.

## Testnet Verification

Praxis targets Binance Spot testnet for the current paper-trading path.

Provide credentials through either:

- a repo-root `.env` file
- shell environment variables

Example:

```bash
export BINANCE_TESTNET_API_KEY='your_key'
export BINANCE_TESTNET_API_SECRET='your_secret'
```

Then run:

```bash
uv run pytest tests/testnet/ -v -o 'addopts='
```

Or, if you installed with `pip`:

```bash
python -m pytest tests/testnet/ -v -o 'addopts='
```

Unauthenticated tests cover public endpoints such as ping, server time, exchange info, and order book. Authenticated tests require working testnet credentials. Tests skip when the testnet is unreachable.

## Expected Outputs

- the default suite should validate domain logic, execution state projection, adapters, launcher wiring, concurrency, and shutdown behavior
- explicit testnet runs should validate Binance Spot testnet reachability and adapter correctness

## Read Next

- [Launcher](Launcher.md)
- [Trade Lifecycle](Trade-Lifecycle.md)
- [Venue Adapter](Venue-Adapter.md)
- [Technical Debt](TechnicalDebt.md)
