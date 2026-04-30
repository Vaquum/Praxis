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

---

## TD-021: Per-cancel REST has no individual timeout in `Trading.stop()`

**Origin**: Round-7 audit (Praxis issue #77)
**Severity**: Major (degraded-network only)
**Module**: `praxis/trading.py:332-357`

The shutdown drain loop in `Trading.stop()` calls `await self._venue_adapter.cancel_order(...)` for each open order with no per-call timeout. With `_request_with_retry` (up to 3 attempts × 30s session timeout) a single hung cancel can stall up to 90s. The outer `loop.time() + shutdown_timeout` deadline guards the post-cancel drain wait but not the cancel loop itself. Under transient testnet network stalls, `trading.stop()` can run far beyond `shutdown_timeout`; the launcher's `future.result(timeout=30)` then raises `TimeoutError` and the SQLite WAL `conn.close()` is skipped. SQLite WAL recovery handles this safely on next boot, but the abandoned daemon loop thread may execute briefly against a closed DB before OS reclaim.

**When to fix**: Before any sustained mainnet deployment where shutdown latency matters.
**Migration**: Wrap each cancel in `asyncio.wait_for(adapter.cancel_order(...), timeout=2.0)` with broad-except-and-continue inside the drain loop.

---

## TD-022: Sequential N×30s Nexus thread join in `Launcher._shutdown`

**Origin**: Round-7 audit (Praxis issue #77)
**Severity**: Major (multi-account only)
**Module**: `praxis/launcher.py:1241-1243`

`_shutdown` joins Nexus threads serially (`for thread in self._nexus_threads: thread.join(timeout=30)`). With N accounts, total nexus-shutdown wait is up to N×30s before `trading.stop()` even starts. For paper trade (N=1) this is irrelevant; for any future multi-account deployment the timing compounds and `trading.stop()`'s 30s budget may be exhausted before its drain loop runs.

**When to fix**: Before deploying with more than one Nexus instance per process.
**Migration**: Run the N joins concurrently via `concurrent.futures.wait(threads, timeout=30)` or a small ThreadPoolExecutor.

---

## TD-023: `_accepted_commands` and `_command_trade_ids` registries grow unbounded

**Origin**: Round-7 audit (Praxis issue #77)
**Severity**: Low (long-running sessions)
**Module**: `praxis/core/execution_manager.py:135-137`

`_accepted_commands: dict[str, str]` and `_command_trade_ids` accumulate one entry per `submit_command` call and are never pruned. `_terminal_commands` (separate set used only for the abort guard) is also unbounded. Same class as the now-fixed PT-FIX-39 (`OutcomeTranslator._terminal_command_ids`) and the deferred TD-020 (`command_strategy_ids`). At MMVP testnet throughput this is negligible; over multi-day paper-trade or production runs it warrants pruning.

**When to fix**: Before sustained multi-day paper-trade or any production run.
**Migration**: Same pattern as PT-FIX-39 — replace with `OrderedDict` LRU caches with size cap; evict FIFO on insertion past the cap. Consider a single registry with all per-command metadata to avoid drift between dicts.

---

## TD-024: Shutdown 30s + 30s timeout stack under broken WS

**Origin**: Round-6 audit (Praxis issue #77)
**Severity**: Low (degraded shutdown ergonomics)
**Module**: `praxis/launcher.py:_shutdown`, `praxis/trading.py:Trading.stop`

When the WS connection dies just before SIGTERM, the Nexus thread's `ShutdownSequencer.shutdown()` hits its `_wait_terminal` 30s timeout (no terminal outcomes arrive because WS is dead). `Launcher._shutdown` then waits another 30s in `trading.stop()`'s order-cancel drain. Total shutdown time exceeds 60s where the user might expect prompter exit.

**When to fix**: When operator-facing shutdown UX matters (e.g., CI/CD pipelines, container orchestrators with hard kill timeouts).
**Migration**: Detect WS-down condition (e.g., `_user_streams[...].connected is False`) and short-circuit `_wait_terminal` to escalation, OR pass a unified deadline through both phases.

---

## TD-025: `TradingState.orders` / `closed_orders` / `trade_strategy_ids` not lock-protected

**Origin**: Greybeard pre-PR review of `feat/paper-trade-readiness-fixes`
**Severity**: Low (paper trade), Major (production with cross-thread readers)
**Module**: `praxis/core/trading_state.py:60-78,233-345`

PT-FIX-10 added `_positions_lock` around `positions` reads/writes only. The other dicts mutated by `apply()` on the event-loop thread — `orders`, `closed_orders`, `trade_strategy_ids` — are not lock-protected. `get_trading_state()` returns a live reference to the `TradingState` instance, so any caller reading those dicts from a non-loop thread races the writes. Today no hot-path consumer does this (positions snapshots are the only documented use), so the bug is latent.

**When to fix**: When the first cross-thread consumer of `TradingState.orders` lands, or before any production deployment with metrics/dashboards reading order state.
**Migration**: Either widen `_positions_lock` to cover all four dicts (rename `_state_lock`) and add `snapshot_orders()` / `snapshot_trade_strategy_ids()` mirroring `snapshot_positions()`, OR document that `TradingState` mutation is event-loop-thread-only and force all consumers through accessor methods that snapshot under the lock.

---

## TD-026: `OutcomeTranslator` terminal-dedup eviction silently emits stray Nexus outcomes

**Origin**: Greybeard pre-PR review of `feat/paper-trade-readiness-fixes`
**Severity**: Low (bounded by 10000-command FIFO + downstream rejection)
**Module**: `praxis/outcome_translator.py:155-159,172-180`

When a duplicate Praxis terminal outcome arrives for a `command_id` that has already been evicted from `_terminal_command_ids` (FIFO at `terminal_dedup_cap=10000`), the translator does NOT detect the duplicate and emits a fresh Nexus terminal outcome. `OutcomeProcessor` rejects it with `INVARIANT_BREACH: order not found`, so the operational impact is bounded to a noise log and a no-op. The current docstring frames this as "downstream rejects it" — accurate but downplays that the seam emitted a wrong event we cannot detect locally.

**When to fix**: If duplicate-terminal traffic ever turns the noise-log into operational signal-to-noise problems, or before any deployment where `OutcomeProcessor`'s `INVARIANT_BREACH` rejections are surfaced as alerts.
**Migration**: Replace the in-memory dedup window with a content-addressed marker (e.g., the spine's `TradeOutcomeProduced` sequence number) so dedup survives restart and arbitrary lookback, OR raise `terminal_dedup_cap` to a multi-week working set.

---

## TD-027: Two-lock window in `Launcher.process_outcome` terminal cleanup

**Origin**: Greybeard pre-PR review of `feat/paper-trade-readiness-fixes`
**Severity**: Low (transient, no current consumer trips it)
**Module**: `praxis/launcher.py:1500-1533`

`process_outcome` releases `command_registry_lock` (after popping `command_contexts` / `command_strategy_ids`) and then re-acquires `positions_lock` to delete the position. A predict tick that runs between the two acquisitions sees a position whose strategy-id mapping has already been popped. Today the strategy-context build path filters positions by `strategy_id` independently of the registry, so the worst case is a tick that briefly observes a position that's about to be removed — benign for current consumers.

**When to fix**: If a future code path resolves positions through `command_strategy_ids`, OR if the registry pop and the position deletion need to be atomic for crash-consistency reasons.
**Migration**: Hold a single shared lock through both mutations, OR adopt a single per-account state lock and drop the two-lock split entirely.


## TD-029: `command_contexts` and `command_strategy_ids` leak when `_grow_position` / `_reduce_position` raises

**Origin**: Round-14 8-pass aggregation
**Severity**: Low (bounded; few raise sites)
**Module**: `praxis/launcher.py:1547-1558` (cleanup); cross-repo `nexus/infrastructure/praxis_connector/outcome_processor.py:325-381` (raise sites)

`process_outcome`'s registry purge (`command_contexts.pop` / `command_strategy_ids.pop`) sits behind `if outcome.outcome_type.is_terminal:` AFTER `outcome_processor.process(...)`. A `RuntimeError` from `_grow_position` (`outcome_processor.py:341, 348`) or `_reduce_position` (`:380, 386, 396`) unwinds the call site, skipping the purge. OutcomeLoop's outermost catch swallows it. Memory grows on each defective outcome.

**When to fix**: When defective outcomes are observed in production (e.g., venue ID drift causing missing trade_id), OR when long-running deployments accumulate measurable memory growth.
**Migration**: Wrap `outcome_processor.process(...)` in try/finally that unconditionally runs the registry purge for terminal types, OR couple with Nexus TD-048 (post-success exception path) for a unified fix.

---

## TD-030: `OutcomeTranslator` `fee_rate=0` latent inconsistency with capital reserve estimate

**Origin**: Round-13 audit, re-verified round-14
**Severity**: Low (latent; safe under fee_rate=0)
**Module**: `praxis/launcher.py:1037` (translator default `fee_rate=_ZERO`); `praxis/launcher.py:105` (`_DEFAULT_FEE_RATE = Decimal('0.001')` for capital reserve estimate)

Capital reserve at action-submit time uses `_DEFAULT_FEE_RATE = 0.001`. Translator emits `actual_fees=0` because `fee_rate=_ZERO`. `order_fill` reconciles via the `fee_delta > 0` branch (`capital_controller.py:759-760`). Currently safe. If a future deployment switches `OutcomeTranslator.fee_rate` to non-zero AND the venue actually charges more than estimated, `fee_delta < 0` and `abs(fee_delta) > fee_reserve` (which starts at zero) → `order_fill` returns `EXPECTED_MISS` → position FAILS to grow on FILL → silent state drift.

**When to fix**: Before any deployment switches `OutcomeTranslator.fee_rate` to non-zero. Couples with Nexus TD-051 (realized_pnl exit-fee accounting).
**Migration**: Bring translator `fee_rate` in line with the validator's `_DEFAULT_FEE_RATE`, OR document the asymmetry and gate any future fee_rate change on a `_reduce_position` exit-fee accounting update.

---

## TD-031: `OutcomeTranslator` REJECTED branch asymmetry vs CANCELED / EXPIRED

**Origin**: Round-13 audit (REBUTTAL → docs-only)
**Severity**: Documentation only (safe under current flow)
**Module**: `praxis/outcome_translator.py:143-146,193-209`

CANCELED / EXPIRED branches handle `delta_size > 0 → emit PARTIAL` pattern; REJECTED does not. Verified safe: under MMVP venue flow REJECTED never carries an unflushed delta because the WS PARTIAL has already landed (the implied PARTIAL was already emitted by an earlier WS pass before the reject). Asymmetry by design.

**When to fix**: When a future translator refactor unifies the terminal branches, OR when a venue path emits REJECTED with `delta_size > _ZERO` and no preceding PARTIAL.
**Migration**: Add a code-adjacent comment at `outcome_translator.py:143-146` explaining the asymmetry and the assumed prior-PARTIAL invariant; OR add a sentinel branch matching CANCELED/EXPIRED for symmetric handling.

---

## TD-032: `_build_partial` divide-by-zero risk under malformed venue payload

**Origin**: Round-13 audit (currently guarded)
**Severity**: Documentation only (safe under current call-site guards)
**Module**: `praxis/outcome_translator.py:244` (`delta_price = delta_notional / delta_size`)

Reachable only via direct call with `delta_size == _ZERO`. Currently guarded at `outcome_translator.py:166` (PARTIAL path) and `:194` (CANCELED/EXPIRED path) — every call site checks `if delta_size > _ZERO` first. Safe today but fragile.

**When to fix**: When a future translator refactor adds a new call site for `_build_partial`.
**Migration**: Add a defensive `assert delta_size > _ZERO` (or explicit raise) at function entry rather than relying on caller guards.

---

## TD-033: Praxis ExecutionManager registries grow without purge

**Origin**: Round-14 8-pass aggregation
**Severity**: Low (slow leak; scales linearly with throughput)
**Module**: `praxis/core/execution_manager.py:139-140,304`

`_accepted_commands` (line 139), `_terminal_commands` (line 140), `_command_trade_ids` (populated at line 304) all grow on event arrival with no `pop` / `discard` / `del` anywhere. Bounded by command issuance rate over process lifetime. At MMVP rates this is far from OOM but scales linearly.

**When to fix**: Before long-running (>weeks) single-process deployments, OR when memory monitoring shows growth.
**Migration**: Purge `_accepted_commands` and `_command_trade_ids` on terminal `TradeOutcomeProduced` (mirror `_commands.pop` at `_build_outcome`); cap `_terminal_commands` with LRU eviction or rotate per epoch.

---

## TD-034: Unbounded queues in launcher and ExecutionManager

**Origin**: Round-14 8-pass aggregation
**Severity**: Low (no observability; OOM is the only ceiling)
**Module**: `praxis/launcher.py:1094` (`account_queue: queue.Queue[NexusTradeOutcome]` no `maxsize`); `praxis/core/execution_manager.py:194-196` (`command_queue` / `priority_queue` / `ws_event_queue` likewise)

A stalled consumer (e.g., slow `state_store.append_mutation` synchronous fsync) lets the queue grow without bound. Zero observability into the stall — no metric, no warning. OOM is the only ceiling.

**When to fix**: When operational observability is added, OR when a stalled-consumer incident occurs in paper-trade.
**Migration**: Bounded queues with shed-on-full + WARNING log, OR a watermark-based health metric exposed to HealthLoop so a stall transitions the operational mode.

---

## TD-035: `_emit_ws_outcome` clamp silently drops surplus venue fill

**Origin**: Round-14 8-pass aggregation
**Severity**: Low (mid-run state inconsistency; self-heals on next boot)
**Module**: `praxis/core/execution_manager.py:1320-1332`

When `order.filled_qty > cmd.qty` (duplicate WS fill, venue rounding past target), the code WARNs and clamps the emitted `filled_qty` to `cmd.qty`. Nexus position sized to command target, not venue truth. `_reconcile_capital` next boot detects via "size mismatch — adopting Praxis qty as truth" (`sequencer.py:414-421`), but mid-run the strategy's view of position is undersized and `avg_cost_basis` becomes inconsistent with venue.

**When to fix**: When venue overfill behavior becomes operationally observable, OR when strategies need a consistent mid-run view of venue truth.
**Migration**: Raise an explicit reconcile event (or persist the clamp on the spine) so mid-run state is not silently undersized, OR honor venue truth and let Nexus aggregates absorb the surplus via a `_grow_position` extension.
