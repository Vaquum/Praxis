<div align="center">
  <br />
  <a href="https://github.com/Vaquum"><img src="https://github.com/Vaquum/Home/raw/main/assets/Logo.png" alt="Vaquum" width="150" /></a>
  <br />
</div>
<br />
<div align="center"><b>Vaquum Praxis turns trading decisions into venue orders, durable execution state, and auditable outcomes.</b></div>

<div align="center">
  <a href="#praxis">Praxis</a> •
  <a href="#what-praxis-is-not">What Praxis Is Not</a> •
  <a href="#capabilities">Capabilities</a> •
  <a href="#first-run">First Run</a> •
  <a href="#learn-more">Learn More</a>
</div>
<br />
<div align="center">
  <a href="https://github.com/Vaquum/Praxis/blob/main/docs/README.md"><img src="https://img.shields.io/badge/docs-praxis-blue" alt="Praxis docs" /></a>
  <a href="https://github.com/Vaquum/Praxis/actions/workflows/pr_checks_tests.yml"><img src="https://github.com/Vaquum/Praxis/actions/workflows/pr_checks_tests.yml/badge.svg" alt="PR tests" /></a>
  <a href="https://github.com/Vaquum/Praxis/actions/workflows/pr_checks_ruff.yml"><img src="https://github.com/Vaquum/Praxis/actions/workflows/pr_checks_ruff.yml/badge.svg" alt="Ruff" /></a>
  <a href="https://github.com/Vaquum/Praxis/actions/workflows/pr_checks_mypy.yml"><img src="https://github.com/Vaquum/Praxis/actions/workflows/pr_checks_mypy.yml/badge.svg" alt="Mypy" /></a>
  <a href="https://github.com/Vaquum/Praxis/actions/workflows/pr_checks_codeql.yml"><img src="https://github.com/Vaquum/Praxis/actions/workflows/pr_checks_codeql.yml/badge.svg" alt="CodeQL" /></a>
</div>

<hr />

<a id="praxis"></a>

# Praxis — Execution system

*Event-sourced trade execution system that turns trading decisions into venue orders, durable execution state, and auditable outcomes.*

Praxis unifies order routing, venue communication, lifecycle management, and recovery around a single append-only Event Spine. Persist-before-send order submission means no trade is ever lost to a crash, and startup replay rebuilds state from the durable event log. The current repository is a partial implementation of RFC-4001 ([Praxis issue #1](https://github.com/Vaquum/Praxis/issues/1)); where the RFC and the code diverge, the code is authoritative.

## What Praxis Is Not

Praxis is not:

- the strategy or decision layer
- a generic multi-venue execution platform
- the full RFC-4001 system as written
- a live-trading-hardened production deployment

In the wider Vaquum architecture, Origo sits upstream as the data layer and Limen as the research engine. Nexus turns research outputs into decisions, Praxis executes and tracks those decisions on the venue, and Veritas sits downstream for oversight.

## Capabilities

- Append-only SQLite Event Spine with a tamper-evident SHA-256 hash chain
- Persist-before-send order submission with deterministic client order IDs
- Event-sourced paper trading on Binance Spot testnet
- Support for market, limit, and IOC orders, with stop-loss and take-profit expressed as OCO legs
- Per-account execution routing with isolated credentials and independent account runtimes
- Durable tracking of fills, open orders, closed orders, and per-trade positions
- Per-account double-entry ledger with balances and per-trade realized profit and loss
- Terminal trade outcomes for fills, aborts, cancels, and deadline expiry, delivered through async callbacks for Manager integration
- Venue filter loading and pre-submission validation against Binance trading rules
- Startup replay, venue reconciliation, and WebSocket recovery for crash-safe state rebuilds
- Walk-the-book execution and arrival slippage estimation, surfaced per fill in structured logs
- Binsim in-process Binance simulator and deterministic replay harness for offline runs

## Roadmap

Two execution gaps are tracked for Q3/26:

- Standalone stop, stop-limit, and take-profit submission through the venue adapter ([Praxis issue #171](https://github.com/Vaquum/Praxis/issues/171))
- Execution and arrival slippage fields on `TradeOutcome` ([Praxis issue #172](https://github.com/Vaquum/Praxis/issues/172))

## First Run

The first runnable path is the local test suite followed by an event-sourced `Trading` boot against a fresh Event Spine.

1. Clone the repo and install the package with dev dependencies:

```bash
git clone https://github.com/Vaquum/Praxis.git
cd Praxis
uv pip install -e ".[dev]"
```

Praxis requires Python `>=3.12` and installs its venue, persistence, and observability dependencies from `pyproject.toml`, including `vaquum-nexus` pinned from GitHub; the package is not published on PyPI. The `dev` extra adds the test toolchain, and `pip install -e ".[dev]"` with `python -m pytest` works equally if `uv` is not available. No venue credentials are needed for the install, the test suite, or the first boot; report security concerns through the Vulnerabilities section below.

2. Run the default test suite:

```bash
uv run pytest
```

3. Boot the event-sourced runtime against a fresh Event Spine, which writes `event_spine.sqlite` to the current directory:

```bash
uv run python - <<'EOF'
import asyncio

import aiosqlite

from praxis import Trading, TradingConfig
from praxis.infrastructure.event_spine import EventSpine


async def main() -> None:
    async with aiosqlite.connect('event_spine.sqlite') as conn:
        spine = EventSpine(conn)
        trading = Trading(config=TradingConfig(epoch_id=1), event_spine=spine)
        await trading.start()
        await trading.stop()


asyncio.run(main())
EOF
```

4. Optionally verify Binance Spot testnet access with credentials in `.env` or shell exports:

```bash
echo 'BINANCE_TESTNET_API_KEY=your_key' >> .env
echo 'BINANCE_TESTNET_API_SECRET=your_secret' >> .env
uv run pytest tests/testnet/ -v -o 'addopts='
```

That path verifies the implementation as it exists today: local execution logic by default, then Binance Spot testnet connectivity when credentials and network access are available. Beyond the first run, `praxis.launcher` boots the full per-account runtime with Nexus decision wiring, and the `praxis.binsim` package serves an in-process Binance-shaped venue for offline paper trading.

## Risk Boundary

Praxis is research software. Paper-trading, simulation, and replay outputs are not investment advice, trading advice, live-execution guarantees, regulatory approval, or a promise of future performance. Past performance is not predictive, and trading digital assets can result in total loss of capital.

## Learn more

- Start with the documentation hub in [docs/README.md](https://github.com/Vaquum/Praxis/blob/main/docs/README.md)
- See the target design in [RFC-4001](https://github.com/Vaquum/Praxis/issues/1) and known constraints in [TechnicalDebt.md](https://github.com/Vaquum/Praxis/blob/main/docs/TechnicalDebt.md)
- Start with [Setup-And-Verification.md](https://github.com/Vaquum/Praxis/blob/main/docs/Setup-And-Verification.md) and the runtime walkthroughs in [Trading.md](https://github.com/Vaquum/Praxis/blob/main/docs/Trading.md) and [Trade-Lifecycle.md](https://github.com/Vaquum/Praxis/blob/main/docs/Trade-Lifecycle.md)
- Use [Event-Spine.md](https://github.com/Vaquum/Praxis/blob/main/docs/Event-Spine.md) and [Trading-State.md](https://github.com/Vaquum/Praxis/blob/main/docs/Trading-State.md) for persistence and projections
- Use [Execution-Manager.md](https://github.com/Vaquum/Praxis/blob/main/docs/Execution-Manager.md) for the execution core and [Venue-Adapter.md](https://github.com/Vaquum/Praxis/blob/main/docs/Venue-Adapter.md) for venue integration
- Strengthen recovery understanding with [Recovery-And-Reconciliation.md](https://github.com/Vaquum/Praxis/blob/main/docs/Recovery-And-Reconciliation.md) and [Health.md](https://github.com/Vaquum/Praxis/blob/main/docs/Health.md)
- Analyze execution quality with [Slippage-And-Order-Book.md](https://github.com/Vaquum/Praxis/blob/main/docs/Slippage-And-Order-Book.md) and [Trade-Outcomes.md](https://github.com/Vaquum/Praxis/blob/main/docs/Trade-Outcomes.md)
- Simulate the venue offline with [Binsim.md](https://github.com/Vaquum/Praxis/blob/main/docs/Binsim.md) and verify connectivity with [Binance-Spot-Testnet.md](https://github.com/Vaquum/Praxis/blob/main/docs/Binance-Spot-Testnet.md)
- Read the runtime entry points in [praxis/trading.py](https://github.com/Vaquum/Praxis/blob/main/praxis/trading.py), [praxis/launcher.py](https://github.com/Vaquum/Praxis/blob/main/praxis/launcher.py), and [praxis/trading_inbound.py](https://github.com/Vaquum/Praxis/blob/main/praxis/trading_inbound.py)
- Contribute through the [Developer docs](https://github.com/Vaquum/Praxis/blob/main/docs/Developer/README.md)

## Contributing

Contribution starts from the gap between [RFC-4001](https://github.com/Vaquum/Praxis/issues/1) and the current implementation, through [open issues](https://github.com/Vaquum/Praxis/issues) and [docs changes](https://github.com/Vaquum/Praxis/tree/main/docs). Before contributing, read the code first — the current implementation is the source of truth where it conflicts with the RFC — and start with the [Developer docs](https://github.com/Vaquum/Praxis/blob/main/docs/Developer/README.md).

## Support

Use [GitHub issues](https://github.com/Vaquum/Praxis/issues) for support requests and scope questions.

## Vulnerabilities

Report vulnerabilities privately through [GitHub Security Advisories](https://github.com/Vaquum/Praxis/security/advisories/new). Do not report vulnerabilities through public issues.

## Citations

Published work should cite:

Vaquum Praxis [Computer software]. (2026). Retrieved from [GitHub](https://github.com/Vaquum/Praxis).

## License

[MIT License](https://github.com/Vaquum/Praxis/blob/main/LICENSE).
