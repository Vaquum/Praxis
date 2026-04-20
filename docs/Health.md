# Health

This page explains how Praxis exposes Trading sub-system health to the Manager so the Manager can decide when to throttle, reduce, or halt.

## Two Different Health Concepts

Praxis has two distinct health signals with different consumers:

- `HealthSnapshot` (this page): per-account **trading** health — latency, failure rate, clock drift. Pulled by the Manager on a timer to drive operational-mode decisions (ACTIVE, REDUCE_ONLY, HALT).
- `/healthz` (see [Launcher §Healthz](Launcher.md#healthz)): whole-process **liveness** — is Trading up, is the loop thread alive, are the Nexus threads alive. Probed by the platform (Render) to decide whether to restart the container.

They should not be conflated. A process can be live (`/healthz` 200) but trading-unhealthy (elevated `HealthSnapshot.failure_rate`), in which case the Manager throttles. A process with a crashed Nexus thread will fail `/healthz` and be restarted by the platform.

## What The Health Snapshot Is

`praxis/core/domain/health_snapshot.py` defines `HealthSnapshot`: a frozen point-in-time view of one trading account's REST execution health. Every value is bounded so it can drive a deterministic Manager-side policy without further validation.

Fields:

- `latency_p99_ms`: ack latency p99 over the rolling window
- `consecutive_failures`: count since the last successful REST request
- `failure_rate`: failing fraction of the rolling window, bounded `[0.0, 1.0]`
- `rate_limit_headroom`: venue-wide utilisation, bounded `[0.0, 1.0]`, where `0.0` is idle and `1.0` is at limit
- `clock_drift_ms`: absolute drift from venue server time

Fields default to a healthy zero state when no samples have been collected yet.

The field name `rate_limit_headroom` carries utilisation semantics (higher is worse) for parity with the Manager-side `HealthEvaluator` in Nexus, which already exposes the field under that name. The two sides must agree on the symbol, so the apparent mismatch between the noun `headroom` and its actual contents (`used / limit`) is intentional.

## How Metrics Are Collected

`praxis/core/health_tracker.py` (`HealthTracker`) holds the rolling samples per account. The tracker is fed once per logical REST request from `BinanceAdapter._request_with_retry`, with retries treated as one logical attempt rather than per-attempt rows. The tracker is thread-safe; both `record_request` and `snapshot` take the same lock.

Venue-wide measurements live on the adapter, not the tracker:

- `BinanceAdapter.rate_limit_utilization` is derived from existing weight headers
- `BinanceAdapter.clock_drift_ms` is populated by `sync_clock_drift()` which calls `/api/v3/time`

`BinanceAdapter.get_health_snapshot(account_id)` composes a `HealthSnapshot` from the per-account tracker plus the venue-wide values. Unknown accounts return a default snapshot (zero values) rather than raising.

## How Manager Reads It

The Trading facade exposes the snapshot through `Trading.get_health_snapshot(account_id)`. The method is `async` so a Manager running on its own thread can call it across the asyncio loop boundary without blocking the loop:

```python
fut = asyncio.run_coroutine_threadsafe(
    trading.get_health_snapshot(account_id),
    trading.loop,
)
snapshot = fut.result(timeout=...)
```

The facade requires `Trading.start()` to have been awaited and then delegates straight to the venue adapter.

## Current Scope

The current implementation collects metrics from `BinanceAdapter` REST calls, exposes them through `Trading`, and is consumed by the Manager-side `HealthEvaluator` in Nexus. Push-based delivery (periodic events on the outcome queue) is not implemented; pull is the only contract today.

## Read Next

- [Execution Manager](Execution-Manager.md)
- [Recovery And Reconciliation](Recovery-And-Reconciliation.md)
- [Technical Debt](TechnicalDebt.md)
