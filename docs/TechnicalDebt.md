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

## TD-015: Slippage estimation scales linearly with book depth

**Origin**: PR #66 (review comments)
**Severity**: Low (depth typically ~20 levels, Decimal loop is fast)
**Module**: `praxis/core/estimate_slippage.py`

`estimate_slippage()` walks the order book level-by-level with Decimal arithmetic. For current depth limits (~20 levels), this is fast. NumPy vectorization was attempted but rejected due to precision loss (float64 cannot represent all Decimal values exactly) and disproportionate dependency overhead (~30MB for ~20 levels).

**When to fix**: Before depth limits exceed 100 levels.
**Migration**: If performance becomes an issue, consider Decimal-native cumulative precomputation or early-exit optimizations. Do not use float64 for financial calculations.

---

## TD-018: Clock-drift estimate ignores asymmetric network latency

**Origin**: PR (Health.2 — `feat/TD-health-signals`)
**Severity**: Low (drift only feeds a 3-threshold health gate)
**Module**: `praxis/infrastructure/binance_adapter.py`

`sync_clock_drift()` estimates drift as `abs(serverTime - midpoint(local_before, local_after))`. The midpoint assumes symmetric request/response latency. Real-world latency is rarely symmetric, so the reported drift can be off by half the round-trip time.

**When to fix**: Before clock-drift thresholds are tightened past round-trip noise (current `clock_drift_max_ms` default in Nexus is 500 ms, which absorbs typical asymmetry).
**Migration**: Use a multi-sample method such as Cristian's algorithm with a minimum-RTT round, or rely on system NTP and report the offset reported by the OS instead of probing the venue.
