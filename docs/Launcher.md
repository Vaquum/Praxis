# Launcher

This page explains how Praxis is started as a whole process and how it is wired together with Nexus and shared market data.

## What The Launcher Is

`praxis/launcher.py` is the orchestration entry point for the combined Praxis + Nexus runtime. It is responsible for:

- creating the shared asyncio event loop thread used by Praxis
- opening the Event Spine SQLite connection on that loop
- starting the `Trading` runtime
- constructing an `ArrowPriceStore` over `PRAXIS_ARROW_DIR` and resolving the mark-price `(series, interval)` from the manifest; the Nexus `PredictLoop` polls the Conduit volume at `PRAXIS_CONDUIT_DIR`
- starting one Nexus manager thread per configured account
- serving the `/healthz` HTTP endpoint so Render can probe process liveness
- routing `TradeOutcome` objects back to the correct Nexus thread
- handling shutdown on `SIGINT` and `SIGTERM`

In the current implementation, Praxis is the process. The launcher keeps the execution layer and decision layer in one runtime rather than splitting them into networked services.

## Main Runtime Shape

The current process layout is:

1. main thread for process lifetime and signal handling
2. one asyncio loop thread for Praxis runtime work (hosts Trading, `/healthz`, and the Event Spine connection)
3. one Nexus thread per configured account

Venue REST calls, user-stream processing, reconciliation, execution events, and healthz replies all stay on the Praxis loop, while each Nexus instance runs synchronously in its own thread.

## Startup Order

At a high level, `Launcher.launch()` does this:

1. install signal handlers (no-op if not on the main thread, so tests can drive `launch()` from a worker)
2. start the asyncio event loop thread
3. start `Trading` (opens the Event Spine on the loop when the launcher was given `db_path` instead of a pre-built `EventSpine`)
4. start one Nexus thread per `InstanceConfig`; each thread constructs an `ArrowPriceStore` over `PRAXIS_ARROW_DIR`, resolves the mark-price `(series, interval_seconds)` from the manifest via `_resolve_mark_price_series`, and passes `PRAXIS_CONDUIT_DIR` to the `PredictLoop`
5. start the `/healthz` listener
6. block until `_stop_event` is set (signal, test harness, or external shutdown)
7. shutdown sequence: setting `_stop_event` makes the `/healthz` handler return `503 {"status":"unhealthy","failures":["shutting_down",...]}` immediately (Render sees unhealthy as of the next probe), then the launcher joins each Nexus thread, stops Trading, closes the Spine connection, and only then calls `_stop_healthz` to tear down the listener itself before stopping the event loop

Within each Nexus instance, the launcher wires:

- `PraxisOutbound` so Nexus can submit commands, pull positions, and pull health snapshots
- a per-account `queue.Queue[TradeOutcome]` for outcome delivery back from Praxis
- a `StartupSequencer` that loads the strategy manifest and strategy runtime state

## InstanceConfig

`InstanceConfig` defines one Nexus manager instance:

- `account_id`
- `manifest_path`
- `strategies_base_path`
- `state_dir`
- optional `strategy_state_path`

`account_id` and `allocated_capital` are sourced from the manifest itself (see Nexus `Manifest.account_id` / `Manifest.allocated_capital`). The `account_id` passed to `InstanceConfig` must match the manifest's `account_id:` key — the launcher pre-loads each manifest to extract this value before constructing the config.

The launcher creates one per-account outcome queue and one per-account Nexus thread from these configs.

## Env-Driven Entrypoint

`python -m praxis.launcher` invokes `main()`, which reads configuration from the process environment and starts the runtime. This is the entrypoint the Docker image uses and the one Render calls.

### Required environment

| Var | Purpose |
|---|---|
| `EPOCH_ID` | Event-spine epoch identifier (positive integer) |
| `TRADE_MODE` | Trading mode selector. `paper` routes the venue adapter at `https://testnet.binance.vision` (REST), `wss://stream.testnet.binance.vision` (WebSocket stream — market data), and `wss://ws-api.testnet.binance.vision/ws-api/v3` (WebSocket API — signed requests + user-data-stream `subscribe.signature`); `live` routes all three at `https://api.binance.com`, `wss://stream.binance.com:9443`, and `wss://ws-api.binance.com:443/ws-api/v3`. Endpoints are the `MAINNET_*_URL` / `TESTNET_*_URL` constants in `praxis/infrastructure/binance_urls.py`. Set explicitly per environment — there is no default and no separate URL or testnet env var |
| `MANIFESTS_DIR` | Directory containing per-account manifest YAML files (`*.yaml` / `*.yml`); the launcher enumerates them and spawns one instance per file |
| `STRATEGIES_BASE_PATH` | Base path for resolving strategy `.py` files referenced from manifests. Also prepended to `sys.path` at boot so strategy modules co-located with the strategies directory become importable by the `StartupSequencer` |
| `STATE_BASE` | Root for per-account state; `state_dir = STATE_BASE / <account_id> / <epoch_id>`; event-spine SQLite lives at `STATE_BASE / event_spine.sqlite` (shared file, epoch-scoped by an `epoch_id` column rather than by path) |

### Per-account credentials

For each manifest found under `MANIFESTS_DIR`, the launcher reads:

- `BINANCE_API_KEY_<ACCOUNT_ID>`
- `BINANCE_API_SECRET_<ACCOUNT_ID>`

`<ACCOUNT_ID>` is the manifest's `account_id:` value normalized by uppercasing and replacing non-alphanumeric characters with `_`. For example, `account_id: acct-001` resolves to `BINANCE_API_KEY_ACCT_001` / `BINANCE_API_SECRET_ACCT_001`.

### Optional environment

| Var | Default | Purpose |
|---|---|---|
| `SHUTDOWN_TIMEOUT` | `30` | Seconds to wait for orders to reach terminal state before forcing shutdown |
| `STRATEGY_STATE_BASE` | unset | Base path for strategy state blobs; each instance gets `STRATEGY_STATE_BASE / <account_id> / <epoch_id>`. When unset, strategy state falls back under `state_dir` (`STATE_BASE / <account_id> / <epoch_id> / strategy_state`) |
| `PRAXIS_CONDUIT_DIR` | `/opt/conduit` | Read-only mount of the `furnace_conduit` Docker volume. Contains the serving manifest and per-series prediction Arrow frames that the Nexus `PredictLoop` polls for new signals. Mount as `furnace_conduit:/opt/conduit:ro` on the praxis service |
| `PRAXIS_ARROW_DIR` | `/opt/arrow` | Read-only mount of the `tdw-control-plane_arrow` Docker volume. Contains per-series OHLCV frames (`<series>/latest.arrow`) that `ArrowPriceStore` reads to supply closed-bar `close` prices for ENTER reference pricing and mark-to-market. Mount as `tdw-control-plane_arrow:/opt/arrow:ro` on the praxis service |
| `PRAXIS_MARK_PRICE_SERIES` | unset | Selects which series' OHLCV close backs ENTER reference pricing and mark-to-market. Defaults to the lone `signal.series` declared by the manifest; required when the manifest declares multiple distinct series. When set to a series not present in any manifest strategy, `PRAXIS_MARK_PRICE_INTERVAL_SECONDS` is also required |
| `PRAXIS_MARK_PRICE_INTERVAL_SECONDS` | unset | Bar width in seconds for `PRAXIS_MARK_PRICE_SERIES`. Required only when `PRAXIS_MARK_PRICE_SERIES` names a series not declared by any strategy in the manifest (otherwise the interval is taken from the manifest). Must be a positive integer |
| `PORT` | — | Container orchestrators that inject a port (`docker compose`, k8s, etc.) — bound by the `/healthz` listener |
| `HEALTHZ_PORT` | `8080` | Fallback when `PORT` is not set |
| `LOG_FORMAT` | `json` | `json` routes through `observability.configure_logging` (structlog + orjson); `text` uses stdlib `basicConfig` for local dev |
| `LOG_LEVEL` | `INFO` | Root logger level |
| `NEXUS_PREDICT_POLARS_MAX_THREADS` | `1` | Polars thread count per predict worker process. Applied via `os.environ.setdefault('POLARS_MAX_THREADS', ...)` in the launcher process so spawned interpreters inherit it |
| `NEXUS_UNKNOWN_SUBMISSION_WARN_SECONDS` | `60` | Age (seconds) above which a command still in `SUBMISSION_UNKNOWN` (a `send_command` handoff that timed out, registration retained) is reported by the launcher's `_UnknownSubmissionMonitor` (v0.80.0). Telemetry only — the monitor logs a WARNING with the stuck count, max age, and a bounded id list; it never queries the venue or releases capital |
| `NEXUS_UNKNOWN_SUBMISSION_SCAN_SECONDS` | `15` | Interval (seconds) between `_UnknownSubmissionMonitor` scans (v0.80.0). A `threading.Timer` cadence mirroring `SnapshotScheduler`; each scan re-evaluates the retained unknown-submission set against `NEXUS_UNKNOWN_SUBMISSION_WARN_SECONDS` |

> **Upgrade note (v0.66.0):** `state_dir` and the `STRATEGY_STATE_BASE` tree are now epoch-scoped (`… / <account_id> / <epoch_id>`). On first boot of v0.66.0, state written by ≤v0.65.0 under the old account-level paths (`STATE_BASE / <account_id>`, `STRATEGY_STATE_BASE / <account_id>`) is no longer recovered — even when `EPOCH_ID` is unchanged — so the account starts from a fresh `InstanceState` (`capital_pool` re-read from the manifest, positions rebuilt from the venue by boot reconciliation). This one-time reset is intended; the old directories are left untouched (see TD-068). To preserve continuity across the upgrade, copy the old account-level tree — `STATE_BASE / <account_id>/{snapshots,wal,strategy_state}`, plus `STRATEGY_STATE_BASE / <account_id>/` if that var was set — into the matching `… / <EPOCH_ID>/` subdirectories before starting v0.66.0.

## ArrowPriceStore

`praxis/arrow_price_store.py` supplies closed-bar close prices from the control-plane Arrow volume.

`ArrowPriceStore.latest_close(series, interval_seconds)` reads `<PRAXIS_ARROW_DIR>/<series>/latest.arrow` (an OHLCV IPC frame written by Furnace, carrying `ts`, `open`, `close` — plus `high`, `low`, `volume` — and `start_ts` for dollar series) and returns the latest closed bar's `close` as a `Decimal`. It uses only `ts`/`close`; the replay loader (`load_replay_bars`) also reads `open` to feed the Limen-parity snapshot's entry-bar return. A bar with open timestamp `ts` (Int64 UTC epoch nanoseconds) is closed when `ts + interval_seconds` nanoseconds is at or before now, so the still-forming final bar is excluded.

The method returns `None` — which aborts the MTM tick and yields no fallback price for ENTER actions — when:

- the frame file is absent (transient atomic-swap between Furnace writes)
- the frame is unreadable or malformed (missing `ts` / `close` columns, or `ts` is not Int64 — a `Datetime` or millisecond `ts` would compare meaninglessly against the nanosecond cutoff)
- no bar in the frame is yet closed
- the latest closed bar is staler than approximately three intervals (frozen-feed guard)
- the close value is missing or non-finite

## Healthz

`/healthz` is an in-process `aiohttp` route bound on the launcher's asyncio loop. Render polls it to decide whether to restart the container.

The endpoint returns `200 {"status": "ok"}` only when all of the following hold:

- `Trading.started` is `True`
- the asyncio loop thread is alive
- `_stop_event` has not been set
- every Nexus instance thread is alive

On any failure the response is `503 {"status": "unhealthy", "failures": [...]}` listing which checks failed (`shutting_down`, `trading_not_started`, `loop_thread_dead`, or `nexus_threads_dead:<names>`). During shutdown, setting `_stop_event` is what makes the handler return `503` immediately (the `shutting_down` failure) — the listener itself stays up serving `503` until `_stop_healthz` runs near the end of `_shutdown`, so Render sees `unhealthy` (not connection-refused) for the whole shutdown window.

`/healthz` measures process liveness only. It is a different contract from `HealthSnapshot` (see [Health](Health.md)), which reports per-account trading health to the Manager.

## Logging

`main()` calls `observability.configure_logging(log_level=...)` when `LOG_FORMAT=json` (the default). This routes every log record — from Praxis and Nexus, and any stdlib logger in the process — through structlog with orjson JSON rendering on stdout. `bind_context(epoch_id=...)` runs before the launcher starts so every record inherits `epoch_id` via structlog contextvars.

`LOG_FORMAT=text` falls back to stdlib `basicConfig` with a human-readable format and is intended for local dev only.

JSON-format logs are what make Render log drains (Better Stack / Axiom / S3) useful for audit: the sink can index by `epoch_id`, `account_id`, `command_id`, etc.

## Why This Matters

This design keeps command submission and outcome routing cheap:

- Nexus to Praxis crosses a thread boundary, not a network boundary
- Praxis to Nexus returns outcomes through a thread-safe queue
- all accounts stay isolated at the runtime level even though they share one process
- the Event Spine opens exactly once per process, shared across accounts, on the single Praxis loop

## Current Boundary

The launcher already wires the paper-trading path end to end. It does not implement a microservice deployment model, and it does not introduce independent remote process boundaries between Praxis and Nexus.

## Read Next

- [Trade Lifecycle](Trade-Lifecycle.md)
- [Execution Manager](Execution-Manager.md)
- [Event Spine](Event-Spine.md)
- [Health](Health.md)
