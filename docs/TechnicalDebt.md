# Technical Debt

Known technical debt in shipped code. Each item includes origin PR, severity, and migration path.

---

## TD-009: VWAP re-read from spine on abort

**Origin**: PR #52 (Copilot review)
**Severity**: Low (epochs are small currently)
**Module**: `praxis/core/execution_manager.py`

`_process_abort` computes VWAP by calling `EventSpine.read()` and filtering for `FillReceived` events matching the `client_order_id`. This re-reads and rehydrates the entire epoch for every abort with fills, scaling as O(events_in_epoch). The `Order` dataclass tracks `filled_qty` but not `avg_fill_price`.

**When to fix**: Before epochs grow to thousands of events or abort frequency increases.
**Migration**: Either add cumulative notional tracking to `Order`/`TradingState` so VWAP is available without spine re-read, or add a spine query method that fetches only `FillReceived` rows for a given `client_order_id`.

---

---

---

## TD-015: Slippage estimation scales linearly with book depth

**Origin**: PR #66 (review comments)
**Severity**: Low (depth typically ~20 levels, Decimal loop is fast)
**Module**: `praxis/core/estimate_slippage.py`

`estimate_slippage()` walks the order book level-by-level with Decimal arithmetic. For current depth limits (~20 levels), this is fast. NumPy vectorization was attempted but rejected due to precision loss (float64 cannot represent all Decimal values exactly) and disproportionate dependency overhead (~30MB for ~20 levels).

**When to fix**: Before depth limits exceed 100 levels.
**Migration**: If performance becomes an issue, consider Decimal-native cumulative precomputation or early-exit optimizations. Do not use float64 for financial calculations.

---

## TD-016: Praxis has no Nexus hosting infrastructure

**Origin**: MMVP-X.1 runtime architecture clarification (RFC-3001 #16 comment, RFC-4001 #1 comment)
**Severity**: High (blocks all Nexus ↔ Praxis integration)
**Modules**: `praxis/trading.py`, `praxis/trading_config.py`

Praxis is the only service in the Nexus/Praxis/Limen stack — it owns the asyncio event loop and persistent WebSocket venue connections. Nexus Manager instances (one per account) run as sync threads in the same process. This runtime model was confirmed but Praxis has no infrastructure to support it.

Four things are missing:

### 1. Event loop exposure

Nexus threads need the asyncio event loop reference to call `asyncio.run_coroutine_threadsafe(trading.submit_command(...), loop)`. Currently `Trading` does not expose its event loop. The loop must be available before Nexus threads start and remain stable for the process lifetime.

### 2. Per-account outcome routing

`TradingConfig.on_trade_outcome` accepts a single `Callable[[TradeOutcome], Awaitable[None]]`. This callback must dispatch outcomes to the correct Nexus instance by `outcome.account_id`. The routing mechanism is a per-account `queue.Queue` (stdlib, thread-safe) — one queue per Nexus instance. The `on_trade_outcome` callback must resolve `account_id → queue` and put the outcome on the right queue. This mapping must be updatable at runtime (accounts can be added/removed via hot reload).

### 3. Shared market data poller

Nexus instances need market data for live feature preparation before `sensor.predict()`. Different sensors use different kline sizes (e.g. 3600s for 1h bars, 900s for 15m bars). The kline size is stored in the Limen manifest's `data_source_config.params['kline_size']` — extract during sensor wiring and add to `WiredSensor`.

A shared poller thread must:
- Fetch klines per unique kline_size across all wired sensors using `binancial.compute.get_spot_klines(client, symbol, kline_size, ...)`
- Maintain a shared rolling polars DataFrame per kline_size
- Provide thread-safe read access for all Nexus instances (one trading pair per process)
- Deduplicate: if sensors A and B both use 3600s bars, one fetch serves both
- This is the Origo market data feed referenced in RFC-3001

### 4. Process entry point / launcher

Nothing currently starts Praxis and spawns Nexus instance threads. A launcher is needed that:
- Creates and starts `Trading` (asyncio event loop, WebSocket connections)
- Starts the shared market data poller thread
- Reads instance configuration (which accounts, which manifests, which experiment directories)
- Spawns one Nexus Manager thread per account, passing:
  - The asyncio event loop reference (for `run_coroutine_threadsafe`)
  - The `Trading` instance reference (for `submit_command`, `pull_positions`)
  - The account's outcome `queue.Queue`
  - The shared market data reference
- Handles process lifecycle: graceful shutdown (stop Nexus threads → stop poller → stop Praxis), hot reload (add/remove accounts)

### Related Praxis concern: TD-014

TD-014 (single-writer concurrency) becomes critical with this architecture. Nexus threads calling `run_coroutine_threadsafe(submit_command(...))` inject work into the event loop from external threads. The command queue serialization in `ExecutionManager` should handle this correctly since `asyncio.Queue.put` from a coroutine scheduled via `run_coroutine_threadsafe` runs inside the event loop. But this must be verified — the current `enqueue_ws_event` path and any direct `TradingState` mutation outside the account coroutine will race with Nexus-originated commands.

**When to fix**: After Nexus MMVP-X.* items are complete. This is the integration layer that ties everything together.
**Migration**: Add event loop accessor to `Trading`, implement outcome dispatch routing in `on_trade_outcome`, build market data poller thread, build the launcher as a new module (e.g. `praxis/launcher.py` or a top-level `main.py`).

