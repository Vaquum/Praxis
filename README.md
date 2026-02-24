<h1 align="center">
  <br>
  <a href="https://github.com/Vaquum"><img src="https://github.com/Vaquum/Home/raw/main/assets/Logo.png" alt="Vaquum" width="150"></a>
  <br>
</h1>

<h3 align="center">Praxis</h3>

<p align="center">
  <a href="#description">Description</a> •
  <a href="#owner">Owner</a> •
  <a href="#setup">Setup</a> •
  <a href="#testnet-verification">Testnet Verification</a> •
  <a href="#integrations">Integrations</a> •
  <a href="#docs">Docs</a>
</p>
<hr>

## Description

Execution system for Vaquum — Trading sub-system + Account sub-system.

## Owner

- [@blahmonkey](https://github.com/blahmonkey)

## Setup

```bash
# Clone
git clone https://github.com/Vaquum/Praxis.git
cd Praxis

# Install dev dependencies
uv pip install -e ".[dev]"
```

## Testnet Verification

Verify connectivity to the Binance Spot testnet (REST + WebSocket).
Testnet tests are **excluded from default `pytest`** — they only run when explicitly invoked.

```bash
# Option A: .env file in repo root (gitignored)
echo 'BINANCE_TESTNET_API_KEY=your_key' >> .env
echo 'BINANCE_TESTNET_API_SECRET=your_secret' >> .env

# Option B: shell exports
export BINANCE_TESTNET_API_KEY='your_key'
export BINANCE_TESTNET_API_SECRET='your_secret'

# Run testnet tests
python -m pytest tests/testnet/ -v -o 'addopts='
```

Tests skip gracefully when the testnet is unreachable or credentials are not set.
Unauthenticated tests (ping, server time, exchange info, order book) run without credentials.

## Integrations

- [Manager](https://github.com/Vaquum/Praxis/issues/2) — Risk management layer that sits between signal generation and Praxis.

## Docs

See [`/docs`](docs/).
