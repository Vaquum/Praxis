# Binsim — In-Process Binance Simulator

Binsim replaces Binance Spot testnet as Praxis's paper-trading venue. It removes testnet-borne incidents (`recvWindow` rejections from clock skew, per-IP weight pinning, generic throttling) and unlocks the same backend for high-speed historical replay later.

For the design rationale see issue [#112](https://github.com/Vaquum/Praxis/issues/112). For implementation details see the `praxis.binsim` package.

## What Binsim Is

A self-contained service that exposes a Binance-shaped REST + WebSocket surface:

| Endpoint | Notes |
|---|---|
| `GET /healthz` | `{"status":"ok"}` — liveness probe |
| `GET /api/v3/time` | `{"serverTime": <unix-ms>}` |
| `GET /api/v3/exchangeInfo` | Static BTCUSDT filter set |
| `GET /api/v3/depth` | Live top-N book from the hosted depth poller |
| `GET /api/v3/account` | Ledger balances in Binance shape (signed) |
| `POST /api/v3/order` | Market orders only; walks the book + applies to ledger atomically (signed) |
| `GET /api/v3/order` | 404 with `-2013` (no non-terminal order state) (signed) |
| `GET /api/v3/openOrders` | `[]` (signed) |
| `GET /api/v3/myTrades` | `[]` (signed) |
| WebSocket `/ws-api/v3` | Accepts `userDataStream.subscribe.signature`, returns `subscriptionId`; pushes no fills |
| WebSocket `/stream` | Accepts the connection, pushes no frames |

The order book is replaced wholesale every 1s from the hosted depth-20 service at `binance-spot-depth20-1000ms.onrender.com`. Market-order fills walk this snapshot for VWAP. A staleness gate rejects orders with Binance code `-1003` if the last successful poll is older than the configured threshold.

## Swap From Testnet To Binsim

Praxis's launcher resolves venue URLs from `TRADE_MODE` + an optional `BINSIM_URL` override. When `BINSIM_URL` is set under `TRADE_MODE=paper`, all three URLs (REST, WS-stream, WS-API) derive from it **and** the market-data poller is routed to Binance Spot mainnet (so sensors see the same data distribution binsim is matching against):

| Praxis env | Without binsim | With binsim |
|---|---|---|
| `TRADE_MODE` | `paper` | `paper` (unchanged) |
| `BINSIM_URL` | unset | `http://binsim:8081` |
| REST URL (derived) | `https://testnet.binance.vision` | `http://binsim:8081` |
| WS URL (derived) | `wss://stream.testnet.binance.vision` | `ws://binsim:8081` |
| WS-API URL (derived) | `wss://ws-api.testnet.binance.vision/ws-api/v3` | `ws://binsim:8081/ws-api/v3` |
| Market-data feed (`binancial` per-minute) | `testnet.binance.vision` | `api.binance.com` (**mainnet**) |

`https://` in `BINSIM_URL` produces `wss://` WS URLs; `http://` produces `ws://`. `BINSIM_URL` is a hard error under `TRADE_MODE=live` so the override cannot accidentally divert mainnet traffic.

The mainnet market-data routing under binsim is deliberate: binsim is a fully internal venue with its own mainnet-quality depth feed (the spec — Praxis#112 "Order book — live source" — polls mainnet-mirror depth at 1s cadence). Feeding sensors with sparse testnet aggTrades while binsim fills against mainnet depth would defeat the sim's purpose. The MAJOR-001 safety property (no paper-orders against mainnet data) only applies when paper orders reach a real venue; binsim orders never do.

To make `ws://` URLs reachable, Praxis's WS-API connector gates the relaxation behind the `BINSIM_URL` env var being set — production deployments without `BINSIM_URL` retain the original fail-closed `wss://`-only behavior.

### Step-by-step swap

1. **Register accounts on binsim** (one-shot per account). The CLI mints an api_key and prints it on stdout:

   ```bash
   docker exec binsim python -m praxis.binsim register \
       --account-id acc-1 \
       --initial-usdt 10000 \
       --initial-btc 0
   # prints: a1b2c3...64-hex-chars...e9f0
   ```

   Store the printed api_key — the binsim never reveals it again. (Only a SHA-256 hash is persisted; lookup is hash-based at request time.)

2. **Set Praxis env** to point at binsim. Per-account credentials use the same env names as testnet — only the value changes:

   ```bash
   # Existing testnet env
   TRADE_MODE=paper
   BINANCE_API_KEY_acc-1=<testnet-key>
   BINANCE_API_SECRET_acc-1=<testnet-secret>

   # Swap to binsim
   TRADE_MODE=paper
   BINSIM_URL=http://binsim:8081
   BINANCE_API_KEY_acc-1=<api_key printed by `register` above>
   BINANCE_API_SECRET_acc-1=binsim-secret  # any non-empty string; binsim does presence check only
   ```

3. **Restart Praxis**. The launcher resolves the URLs via `_resolve_trade_mode`, the WS connector accepts `ws://` because `BINSIM_URL` is set, and all REST + WS traffic from `BinanceAdapter` and `BinanceWS` flows to binsim.

To revert: unset `BINSIM_URL`. Praxis falls back to testnet immediately on next restart.

## Required Binsim Environment

| Env | Required | Default | Notes |
|---|---|---|---|
| `BINSIM_DEPTH_TOKEN` | yes | — | Bearer for `binance-spot-depth20-1000ms.onrender.com/top20` |
| `BINSIM_STATE_DIR` | yes | — | Where the ledger snapshot lives (mount a host directory) |
| `BINSIM_HOST` | no | `0.0.0.0` | Container service bind host |
| `BINSIM_PORT` | no | `8081` | Container service bind port |
| `BINSIM_DEPTH_URL` | no | hosted URL | Override only for alt-source experiments |
| `BINSIM_STALENESS_MS` | no | `5000` | Order-rejection threshold |
| `BINSIM_POLL_INTERVAL_MS` | no | `1000` | Poll cadence to the depth source |
| `BINSIM_MIN_TOP20_DEPTH_BTC` | no | `0.05` | Reject snapshots whose top-20 depth on either side sums below this floor; book + `last_success_ts_ms` stay untouched so the 5 s HTTP staleness gate surfaces the upstream as `-1003`. Must be a positive, finite Decimal |
| `BINSIM_MAX_STUCK_UPDATE_ID_POLLS` | no | `5` | Reject after this many consecutive polls returning the same `lastUpdateId`. Meaningful minimum is `2` (baseline + one repeat); the parser rejects `1` to prevent silently bricking the feed |

## Sample `docker-compose` Wiring

Append to `/opt/praxis/docker-compose.yml` on the production host, alongside the existing `praxis` service. The state-dir bind-mount uses a host path owned by `uid 1000` (the in-container `binsim` user — same uid as `praxis`, so a single host user owns all bind-mount paths):

```yaml
services:
  binsim:
    image: ghcr.io/vaquum/praxis-binsim:0.61.0
    environment:
      BINSIM_DEPTH_TOKEN: ${BINSIM_DEPTH_TOKEN:?required}
    volumes:
      - type: bind
        source: ./binsim
        target: /var/lib/binsim
        read_only: false
    restart: unless-stopped

  praxis:
    # ... existing block — only changes:
    environment:
      TRADE_MODE: paper
      BINSIM_URL: http://binsim:8081
      # ... rest of existing env including BINANCE_API_KEY_* / BINANCE_API_SECRET_*
    depends_on:
      - binsim
```

Then on the host:

```bash
mkdir -p /opt/praxis/binsim
chown 1000:1000 /opt/praxis/binsim

docker compose pull binsim
docker compose up -d binsim

# Register an account (one-time)
docker compose exec binsim python -m praxis.binsim register \
    --account-id acc-1 --initial-usdt 10000

# Set the printed api_key in /opt/praxis/.env, then:
docker compose up -d praxis
```

## Operational Notes

- **First boot** is fast (no Limen HF download — that's a Praxis-side concern). Healthcheck `start-period` is 30s.
- **Snapshot durability** — every order writes the full ledger snapshot atomically via `tempfile + Path.replace`. Same pattern as Praxis's `_atomic_write_main_cache_state`.
- **API key recovery** — there is none. The plaintext key is returned exactly once from `register`; only a SHA-256 hash persists. If the operator loses it, the recovery path is: stop binsim → wipe `BINSIM_STATE_DIR` (loses all balances) → re-`register` → distribute new key → restart Praxis with the new key.
- **Concurrent register + server** is unsupported. Both processes write the same ledger snapshot file with no inter-process lock. Stop binsim before running `register`.
- **Staleness gate** trips with HTTP 503 + Binance code `-1003` when the depth poller falls behind. Praxis's adapter maps this to `TransientError` and the strategy decides retry policy.
- **Account-key mismatch** between Praxis env and binsim ledger surfaces as HTTP 401 ("unknown API key") on every signed call. Re-run `register` for the missing account, copy the new key, restart Praxis.

For known MMVP gaps (LOT_SIZE filter enforcement, per-account fee rate, unbounded dedup set growth) see TD-064, TD-065, TD-066 in [TechnicalDebt.md](TechnicalDebt.md).
