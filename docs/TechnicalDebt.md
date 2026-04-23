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

---

## TD-019: MarketDataPoller refetches the full window on every tick

**Origin**: PR #72 (Copilot review)
**Severity**: Low for MMVP paper trading; moderate at production cadence
**Module**: `praxis/market_data_poller.py`

`_fetch()` computes `start_date` as `now - n_rows * kline_size` on every poll and refetches the full window (default `n_rows=5000`). At short polling intervals this generates unnecessary REST traffic and can press against Binance rate limits once multiple `kline_size` buckets or multiple accounts share the poller. The current behavior predates this PR; the binancial migration preserved the same pattern.

**When to fix**: Before increasing poll frequency, adding multiple `kline_size` buckets, or going live on mainnet.
**Migration**: Track the highest `close_time` already in `_data[kline_size]` and refetch only from there forward, merging new rows into the in-memory DataFrame. Deduplicate on `close_time` to handle the always-partial last candle. Cap stored history at `n_rows` rolling.

---

## TD-020: `command_strategy_ids` registry grows unbounded per account

**Origin**: PR #73 (zero-bang review)
**Severity**: Low (negligible at MMVP throughput)
**Module**: `praxis/launcher.py`

The per-account `command_strategy_ids: dict[str, str]` registry built inside `Launcher._build_nexus_runtime` records `command_id → strategy_id` on every `SubmissionStatus.SUBMITTED` outcome from `submit_actions`, but no entry is ever removed. At MMVP testnet throughput (~100 commands/day per account) the long-run footprint is negligible (~1 MB/year), but a long-lived production process accumulating thousands of commands per day per account would eventually warrant pruning.

**When to fix**: Before sustained mainnet operation past a few weeks per process.
**Migration**: Have the OutcomeLoop drop `command_strategy_ids[outcome.command_id]` after dispatching a terminal `TradeOutcomeType` (`FILLED`, `REJECTED`, `EXPIRED`, `CANCELED`). Non-terminal outcomes (`ACK`, `PARTIAL`) keep the entry so subsequent fills still resolve.
