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

## TD-016: Nexus hosting infrastructure

**Origin**: MMVP-X.1 runtime architecture clarification (RFC-3001 #16 comment, RFC-4001 #1 comment)
**Severity**: High (blocks end-to-end integration)
**Modules**: `praxis/trading.py`, `praxis/market_data_poller.py`

Nexus Manager instances run as sync threads in the Praxis process. Three of four hosting pieces are built:

- ~~1. Event loop exposure~~ RESOLVED — `Trading.loop` property
- ~~2. Per-account outcome routing~~ RESOLVED — `Trading.register_outcome_queue()` / `route_outcome()`
- ~~3. Shared market data poller~~ RESOLVED — `MarketDataPoller` with per-kline-size threads via TDW
- 4. Process launcher — not built

### 4. Process entry point / launcher

Nothing currently starts Praxis and spawns Nexus instance threads. A launcher is needed that:
- Creates and starts `Trading` (asyncio event loop, WebSocket connections)
- Starts `MarketDataPoller` with kline_intervals derived from manifests
- Reads instance configuration (accounts, manifests, experiment directories)
- Spawns one Nexus Manager thread per account with: loop, Trading ref, outcome queue, market data poller
- Handles graceful shutdown: stop Nexus threads → stop poller → stop Praxis
- Handles hot reload: add/remove accounts at runtime

**When to fix**: Before end-to-end paper trading.
**Migration**: Build launcher as `praxis/launcher.py` or top-level `main.py`.

---

## TD-017: MarketDataPoller cannot add kline_sizes at runtime

**Origin**: MMVP-TD market data poller implementation
**Severity**: Medium (requires process restart to add new kline sizes)
**Module**: `praxis/market_data_poller.py`

`MarketDataPoller` accepts `kline_intervals` at construction. If a strategy author adds a sensor with a new kline_size via manifest hot reload, the poller has no way to start fetching it without restart. Need `add_kline_size(size, interval)` and `remove_kline_size(size)` methods that start/stop per-kline-size threads at runtime.

**When to fix**: When manifest hot reload is built (Nexus TD-022).
**Migration**: Add thread-safe runtime registration of kline_sizes with corresponding poller threads.

