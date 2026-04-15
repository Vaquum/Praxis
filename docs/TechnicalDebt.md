# Technical Debt

Known technical debt in shipped code. Each item includes origin PR, severity, and migration path.

---

## TD-002: Mutable domain models lack post-construction invariant guards

**Origin**: PR #24 (review comments)
**Severity**: Medium
**Modules**: `praxis/core/domain/order.py`, `praxis/core/domain/position.py`

`Order` and `Position` are mutable dataclasses. Validation runs in `__post_init__` only. After construction, direct attribute assignment can violate invariants (e.g. negative `qty`, `filled_qty > qty`). `TradingState` is the intended mutation controller, but nothing enforces that constraint.

**When to fix**: Before any code path mutates `Order`/`Position` outside of `TradingState`.
**Migration**: Add `__setattr__` guards, property setters with validation, or make fields private with validated mutator methods.

---

## TD-004: FillReceived append atomicity relies on caller discipline

**Origin**: PR #31 (review comments)
**Severity**: Medium
**Module**: `praxis/infrastructure/event_spine.py`

`append()` for `FillReceived` performs two INSERTs: first into `fill_dedup`, then into `events`. If the second fails after the first succeeds, the dedup table is polluted and subsequent valid fills are silently dropped. The docstring states callers own transaction boundaries, but this is not enforced.

**When to fix**: Before production use with real fill data.
**Migration**: Enforce transaction context via `SAVEPOINT`, or validate that a transaction is active before executing the dual-insert path.

---

## TD-009: VWAP re-read from spine on abort

**Origin**: PR #52 (Copilot review)
**Severity**: Low (epochs are small currently)
**Module**: `praxis/core/execution_manager.py`

`_process_abort` computes VWAP by calling `EventSpine.read()` and filtering for `FillReceived` events matching the `client_order_id`. This re-reads and rehydrates the entire epoch for every abort with fills, scaling as O(events_in_epoch). The `Order` dataclass tracks `filled_qty` but not `avg_fill_price`.

**When to fix**: Before epochs grow to thousands of events or abort frequency increases.
**Migration**: Either add cumulative notional tracking to `Order`/`TradingState` so VWAP is available without spine re-read, or add a spine query method that fetches only `FillReceived` rows for a given `client_order_id`.

---

## TD-013: replay_events lacks command context for abort processing

**Origin**: PR #59 (Copilot review)
**Severity**: Medium (aborts for replayed commands will be dropped)
**Module**: `praxis/core/execution_manager.py`

`replay_events()` populates `_accepted_commands`/`_terminal_commands` but does not rebuild `_commands` metadata. `_process_abort()` requires `self._commands[command_id]` to look up `order_type`/`symbol`, so aborts for replayed (pre-restart) commands will be accepted by `validate_trade_abort` but then ignored as "abort for unknown command".

**When to fix**: Before supporting abort operations that span restarts.
**Migration**: Either reconstruct the minimal command data needed for aborts during replay (from `OrderSubmitIntent`), or update the abort path to operate from `TradingState` orders without requiring `_commands`.

---

## TD-014: Single-writer concurrency — audit findings

**Origin**: Deep audit (MMVP closure review)
**Severity**: ~~Critical~~ Low (mitigated by existing architecture)
**Modules**: `praxis/trading.py`, `praxis/core/execution_manager.py`

**Audit (MMVP-TD-014.1)**: All `TradingState` mutations already flow through the single-writer path:

- `enqueue_ws_event()` puts events onto `asyncio.Queue` (line 428) → account coroutine drains via `_account_loop` (line 534) → `trading_state.apply(event)` (line 537)
- `_on_execution_report` (WS handler, line 526) → calls `enqueue_ws_event` → goes through queue ✓
- `_reconcile_fills` (line 419) → calls `enqueue_ws_event` → goes through queue ✓
- `_reconcile_terminal` (line 474) → calls `enqueue_ws_event` → goes through queue ✓
- All command processing (`_process_command`) runs inside the account coroutine ✓
- All reads from `TradingState` (order lookups in `_on_execution_report`, `_reconcile_account`) run on the event loop thread — no preemption in asyncio cooperative scheduling ✓

With Nexus integration via `run_coroutine_threadsafe`, scheduled coroutines also run on the event loop thread — no thread-safety violation.

**Remaining caveat**: `asyncio.Queue.put_nowait` (used by `enqueue_ws_event`) is not thread-safe. All current callers are on the event loop thread so this is safe today. If a future code path calls `enqueue_ws_event` from a non-event-loop thread, it would corrupt the queue. Consider adding a thread-safety assertion or using `loop.call_soon_threadsafe` as a guardrail.

**Status**: Mitigated. Original concern (direct TradingState mutation outside coroutine) does not exist — the queue architecture was already correct.

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

