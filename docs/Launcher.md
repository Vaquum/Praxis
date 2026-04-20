# Launcher

This page explains how Praxis is started as a whole process and how it is wired together with Nexus and shared market data.

## What The Launcher Is

`praxis/launcher.py` is the orchestration entry point for the combined Praxis + Nexus + Limen runtime. It is responsible for:

- creating the shared asyncio event loop thread used by Praxis
- opening the Event Spine SQLite connection on that loop
- starting the `Trading` runtime
- starting the shared `MarketDataPoller`
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
4. one or more daemon poller threads for shared market data buckets

That means venue REST calls, user-stream processing, reconciliation, execution events, and healthz replies all stay on the Praxis loop, while each Nexus instance runs synchronously in its own thread.

## Startup Order

At a high level, `Launcher.launch()` does this:

1. install signal handlers (no-op if not on the main thread, so tests can drive `launch()` from a worker)
2. start the asyncio event loop thread
3. start `Trading` (opens the Event Spine on the loop when the launcher was given `db_path` instead of a pre-built `EventSpine`)
4. start `MarketDataPoller`
5. start one Nexus thread per `InstanceConfig`
6. start the `/healthz` listener
7. block until `_stop_event` is set (signal, test harness, or external shutdown)
8. stop `/healthz` first so Render sees unhealthy immediately, then stop Nexus threads, poller, Trading, close the Spine connection, and stop the event loop

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
| `VENUE_REST_URL` | Venue REST base URL |
| `VENUE_WS_URL` | Venue WebSocket base URL |
| `MANIFESTS_DIR` | Directory containing per-account manifest YAML files (`*.yaml` / `*.yml`); the launcher enumerates them and spawns one instance per file |
| `STRATEGIES_BASE_PATH` | Base path for resolving strategy `.py` files referenced from manifests |
| `STATE_BASE` | Root for per-account state; `state_dir = STATE_BASE / <account_id>`; event-spine SQLite lives at `STATE_BASE / event_spine.sqlite` |

### Per-account credentials

For each manifest found under `MANIFESTS_DIR`, the launcher reads:

- `BINANCE_API_KEY_<ACCOUNT_ID>`
- `BINANCE_API_SECRET_<ACCOUNT_ID>`

`<ACCOUNT_ID>` is the manifest's `account_id:` value normalized by uppercasing and replacing non-alphanumeric characters with `_`. For example, `account_id: acct-001` resolves to `BINANCE_API_KEY_ACCT_001` / `BINANCE_API_SECRET_ACCT_001`.

### Optional environment

| Var | Default | Purpose |
|---|---|---|
| `SHUTDOWN_TIMEOUT` | `30` | Seconds to wait for orders to reach terminal state before forcing shutdown |
| `STRATEGY_STATE_BASE` | unset | Base path for strategy state blobs; each instance gets `STRATEGY_STATE_BASE / <account_id>` |
| `PORT` | — | Render injects this for Web services; used for the `/healthz` listener |
| `HEALTHZ_PORT` | `8080` | Fallback when `PORT` is not set |
| `LOG_FORMAT` | `json` | `json` routes through `observability.configure_logging` (structlog + orjson); `text` uses stdlib `basicConfig` for local dev |
| `LOG_LEVEL` | `INFO` | Root logger level |

## Healthz

`/healthz` is an in-process `aiohttp` route bound on the launcher's asyncio loop. Render polls it to decide whether to restart the container.

The endpoint returns `200 {"status": "ok"}` only when all of the following hold:

- `Trading.started` is `True`
- the asyncio loop thread is alive
- `_stop_event` has not been set
- every Nexus instance thread is alive

On any failure the response is `503 {"status": "unhealthy", "failures": [...]}` listing which checks failed (`shutting_down`, `trading_not_started`, `loop_thread_dead`, or `nexus_threads_dead:<names>`). `_stop_healthz` runs first during shutdown so Render sees unhealthy immediately instead of waiting for `SHUTDOWN_TIMEOUT`.

`/healthz` measures process liveness only. It is a different contract from `HealthSnapshot` (see [Health](Health.md)), which reports per-account trading health to the Manager.

## Logging

`main()` calls `observability.configure_logging(log_level=...)` when `LOG_FORMAT=json` (the default). This routes every log record — from Praxis, Nexus, Limen, and any stdlib logger in the process — through structlog with orjson JSON rendering on stdout. `bind_context(epoch_id=...)` runs before the launcher starts so every record inherits `epoch_id` via structlog contextvars.

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

- [Deployment on Render](Deployment-Render.md)
- [Trade Lifecycle](Trade-Lifecycle.md)
- [Execution Manager](Execution-Manager.md)
- [Event Spine](Event-Spine.md)
- [Health](Health.md)
