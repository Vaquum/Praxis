<div align="center">
  <br />
  <a href="https://github.com/Vaquum"><img src="https://github.com/Vaquum/Home/raw/main/assets/Logo.png" alt="Vaquum" width="150" /></a>
  <br />
</div>
<br />
<div align="center"><strong>Praxis is the event-sourced execution system for turning trading decisions into venue actions, durable execution state, and auditable outcomes.</strong></div>

<div align="center">
  <a href="#praxis">Praxis</a> •
  <a href="#what-praxis-is-not">What Praxis Is Not</a> •
  <a href="#capabilities">Capabilities</a> •
  <a href="#first-verification">First Verification</a> •
  <a href="#learn-more">Learn More</a>
</div>
<br />

<hr />

# Praxis

Praxis is the execution system.

Praxis unifies order routing, venue communication, lifecycle management, and recovery around a single Event Spine. Persist-before-send order submission means no trade is ever lost to a crash. Startup replay and reconciliation rebuild state from the durable event log.

The current repository is a partial implementation of RFC-4001 ([Praxis issue #1](https://github.com/Vaquum/Praxis/issues/1)). Where the RFC and the code diverge, the code is authoritative.

## What Praxis Is Not

Praxis is not:

- the strategy or decision layer
- a generic multi-venue execution platform
- the full RFC-4001 system as written
- the completed Account sub-system / ledger layer
- a live-trading-hardened production deployment

In the wider Vaquum architecture, Limen produces research outputs, Nexus produces decisions, and Praxis executes and tracks those decisions. The Account sub-system described in the RFC is not yet implemented in this repository.

## Capabilities

- Event-sourced paper trading on Binance Spot testnet
- SingleShot execution with market, limit, IOC, stop, stop-limit, take-profit, TP-limit, and OCO order support
- Per-account execution routing with isolated credentials and independent account runtimes
- Deterministic client order IDs and persist-before-send order submission
- Durable tracking of fills, open orders, closed orders, and per-trade positions
- Async trade outcome callbacks for Manager integration
- Trade abort, cancel, and deadline-expiry handling with terminal outcomes
- Startup replay, reconciliation, and WebSocket recovery for crash-safe state rebuilds
- Venue filter loading and pre-submission validation against Binance trading rules
- Walk-the-book slippage estimation with execution and arrival slippage analytics

## First Verification

The fastest first success is to install the repo, run the local test suite, and then optionally verify Binance Spot testnet connectivity.

1. Install the package and dev dependencies:

```bash
uv pip install -e ".[dev]"
```

2. Run the default test suite:

```bash
python -m pytest
```

3. Optionally verify Binance Spot testnet access:

```bash
# Option A: .env file in repo root (gitignored)
echo 'BINANCE_TESTNET_API_KEY=your_key' >> .env
echo 'BINANCE_TESTNET_API_SECRET=your_secret' >> .env

# Option B: shell exports
export BINANCE_TESTNET_API_KEY='your_key'
export BINANCE_TESTNET_API_SECRET='your_secret'

# Run testnet checks explicitly
python -m pytest tests/testnet/ -v -o 'addopts='
```

That path verifies the current implementation as it exists today: local execution logic by default, then Binance Spot testnet connectivity when credentials and network access are available.

## Learn More

- Start with RFC-4001 in [Praxis issue #1](https://github.com/Vaquum/Praxis/issues/1)
- Review current technical debt in [docs/TechnicalDebt.md](docs/TechnicalDebt.md)
- Read the runtime entry points in [praxis/trading.py](praxis/trading.py), [praxis/launcher.py](praxis/launcher.py), and [praxis/trading_inbound.py](praxis/trading_inbound.py)
- Read the execution core in [praxis/core/execution_manager.py](praxis/core/execution_manager.py) and [praxis/core/trading_state.py](praxis/core/trading_state.py)
- Read persistence and venue integration in [praxis/infrastructure/event_spine.py](praxis/infrastructure/event_spine.py), [praxis/infrastructure/binance_adapter.py](praxis/infrastructure/binance_adapter.py), and [praxis/infrastructure/binance_ws.py](praxis/infrastructure/binance_ws.py)
- Review integration and testnet expectations in [tests/test_launcher.py](tests/test_launcher.py) and [tests/testnet](tests/testnet)

## Contributing

The clearest way to contribute is to work from the gap between RFC-4001 and the current implementation: unsupported execution modes, broader reconciliation and health workflows, and the missing Account sub-system.

Before making changes, read the code first and treat the current implementation as the source of truth when it conflicts with the RFC.

## Vulnerabilities

Report vulnerabilities privately through [GitHub Security Advisories](https://github.com/Vaquum/Praxis/security/advisories/new).

## License

[MIT License](https://github.com/Vaquum/Praxis/blob/main/LICENSE).
