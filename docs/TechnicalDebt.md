# Technical Debt

Known technical debt in shipped code. Each item includes origin PR, severity, and migration path.

---

## TD-009: VWAP re-read from spine on abort — RESOLVED

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

## TD-019: MarketDataPoller refetches the full window on every tick — OBSOLETE (superseded by Conduit migration)

---

## TD-020: `command_strategy_ids` registry grows unbounded per account — RESOLVED

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

---

## TD-029: `command_contexts` and `command_strategy_ids` leak when `_grow_position` / `_reduce_position` raises

**Origin**: Round-14 8-pass aggregation
**Severity**: Low (bounded; few raise sites)
**Module**: `praxis/launcher.py` (`process_outcome` terminal-cleanup block after `outcome_processor.process(...)`); cross-repo `nexus/infrastructure/praxis_connector/outcome_processor.py:325-381` (raise sites)

`process_outcome`'s registry purge (`command_contexts.pop` / `command_strategy_ids.pop`) sits behind `if outcome.outcome_type.is_terminal:` AFTER `outcome_processor.process(...)`. A `RuntimeError` from `_grow_position` (`outcome_processor.py:341, 348`) or `_reduce_position` (`:380, 386, 396`) unwinds the call site, skipping the purge. OutcomeLoop's outermost catch swallows it. Memory grows on each defective outcome.

**When to fix**: When defective outcomes are observed in production (e.g., venue ID drift causing missing trade_id), OR when long-running deployments accumulate measurable memory growth.
**Migration**: Wrap `outcome_processor.process(...)` in try/finally that unconditionally runs the registry purge for terminal types, OR couple with Nexus TD-048 (post-success exception path) for a unified fix.

---

## TD-030: `OutcomeTranslator` `fee_rate=0` latent inconsistency with capital reserve estimate — RESOLVED

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

---

## TD-037: `_process_command` overflow clamp leaves `cumulative_notional` not equal to `filled_qty * avg_fill_price`

**Origin**: Round-17 pre-PR review (Greybeard); narrowed in PR #85 round-6 review
**Severity**: Low (rare overflow guard path; downstream consumers use `cumulative_notional` directly per FINAL-MAJOR-07)
**Module**: `praxis/core/execution_manager.py:1029-1031`

`_process_command`'s immediate-fill overflow clamp scales `total_notional = total_notional * cmd.qty / filled_qty` so the emitted `cumulative_notional` matches the clamped `filled_qty`. That preserves the `cumulative_notional / filled_qty == avg_fill_price` consistency invariant for that single emission. The trade-off is sub-ULP precision drift introduced by the round-trip `(N/q) * (q'/q)` at default Decimal precision — same shape as FINAL-MAJOR-06.

The WS path (`_emit_ws_outcome`) does NOT scale (PR #85 round-6 fix) because there can be a prior PARTIAL emission with the unscaled cumulative; scaling on the overfill clamp could produce a SMALLER cumulative than the previous emission and OutcomeTranslator would compute negative `delta_notional` for the terminal step. The two paths intentionally use different strategies — `_process_command` is one-shot, so monotonicity is not at risk; `_emit_ws_outcome` is multi-emit, so monotonicity wins over per-emission consistency.

**When to fix**: Before tightening sub-ULP invariants on the immediate-fill path, OR before any consumer relies on `cumulative_notional / filled_qty == avg_fill_price` for the WS path (none today — FINAL-MAJOR-07 mandates `cumulative_notional` is read directly).
**Migration**: For `_process_command`, compute the clamp using the per-fill list (sum the prefix that fits within `cmd.qty`) so no division round-trip occurs. For `_emit_ws_outcome`, document the cumulative-vs-clamped-filled inconsistency as expected and add a translator-side defensive log when the inconsistency is observed.

---

## TD-038: `command_registry_lock` chain establishes a new lock-order pair

**Origin**: Round-17 pre-PR review (Greybeard)
**Severity**: Low (no reverse-order caller exists today)
**Module**: `praxis/launcher.py:1494-1543`

The post-FINAL-MAJOR-01 critical section now holds `command_registry_lock` across `capital_controller.send_order` (touches `CapitalController._lock`), `_ensure_entry_position` (takes `positions_lock`), and `_build_order_context` (synchronous work). This establishes two new lock-order pairs:

- `command_registry_lock → CapitalController._lock`
- `command_registry_lock → positions_lock`

Both are consistent with the documented Nexus lock-order chain (`command_registry_lock → positions_lock → CapitalController._lock → _wal_lock`). No existing caller takes them in the reverse order.

**When to fix**: Before introducing any caller that would take `positions_lock` or `CapitalController._lock` and then reach for `command_registry_lock`.
**Migration**: Document the lock-order chain explicitly in `praxis/launcher.py` module docstring; add a runtime lock-order check (`limen` debug-only assertion) in CI to detect inversions early.

---

## TD-039: `command_registry_lock` test exercises a local helper, not the real submitter

**Origin**: Round-17 pre-PR review (Greybeard)
**Severity**: Low (lock invariant is pinned; integration tests cover end-to-end)
**Module**: `tests/test_launcher_command_registry_lock.py:397-559`

`TestFinalMajor01AtomicRegistration` reproduces the post-fix submitter pattern in a module-level helper (`_submitter_pattern_post_final_major_01`) instead of importing `praxis/launcher.py`'s submitter closure directly. The closure is intentionally not extracted because it captures too much state (build_context, fallback_price_provider, validation pipeline outputs). Result: if the real submitter at `launcher.py:1494` regresses to the pre-FINAL-MAJOR-01 split-lock pattern, this test still passes.

**When to fix**: Before the next round of launcher submitter restructuring, or when the cost of an integration harness drops (e.g., a refactor that makes the submitter unit-testable).
**Migration**: Either (a) extract the submitter critical section into a module-level helper that takes the closure-captured state as kwargs and have the test import it, or (b) add an integration test that boots a real `_build_nexus_runtime` and races a fast venue ACK against a slow submitter to assert no torn observation.

---

## TD-040: EventSpine SQLite PRAGMAs are implicit and untested

**Origin**: Round-18 codex-supervised audit (Pass 8)
**Severity**: Low (defaults are durable; no concurrency requirement today)
**Module**: `praxis/launcher.py` (`Launcher._build_event_spine`, the `aiosqlite.connect(str(self._db_path))` call); `praxis/infrastructure/event_spine.py` (`EventSpine.ensure_schema`)

`EventSpine` opens its SQLite database via `aiosqlite.connect(str(self._db_path))` with no PRAGMA statements. Journal mode and synchronous level fall through to SQLite/aiosqlite defaults (`journal_mode=DELETE`, `synchronous=FULL`). Defaults provide ACID durability but not the concurrent-reader semantics of WAL mode. No regression test asserts the chosen settings; a future SQLite or aiosqlite default change could silently flip durability.

**When to fix**: Before adding a concurrent reader (analytics, metrics) against the same DB, OR before any production deployment where durability/perf characteristics are load-bearing.
**Migration**: Issue `PRAGMA journal_mode=WAL` and `PRAGMA synchronous=NORMAL` (typical for WAL + single writer) inside `ensure_schema`. Add a regression test asserting both PRAGMAs survive `ensure_schema`. Document the choice in the EventSpine docstring.

---

## TD-041: Per-outcome `state_store.append_mutation` failure is logged but not propagated

**Origin**: Round-18 codex-supervised audit (Pass 8)
**Severity**: Low at MMVP cadence (next checkpoint heals; Praxis remains source of truth for positions); Major where mid-run risk-state durability matters
**Module**: `praxis/launcher.py` (the `process_outcome` closure inside `Launcher._build_nexus_runtime` — the `state_store.append_mutation(state)` call gated on `result.success and (result.position_updated or result.capital_updated)`)

The launcher's outcome wrapper calls `state_store.append_mutation(state)` after `outcome_processor.process(...)` returns success-with-mutation. The call is wrapped in `try: ... except Exception: _log.exception(...)` per the comment "persistence failure must not abort outcome flow". On failure, in-memory state continues to mutate but the WAL has no STATE_MUTATION entry. There is no counter, no health-loop signal, no mode demotion on repeated failures. Operators only see a log line.

**When to fix**: Before any deployment whose WAL is on flaky storage, OR before alerting/observability on persistence failures becomes load-bearing.
**Migration**: (a) Maintain a per-account counter of consecutive `append_mutation` failures and surface it through `HealthSnapshot` so HealthLoop can demote `state.mode` after N failures, OR (b) propagate the exception to the OutcomeLoop which already logs once and re-raises into the worker's catch-all so the failure is at least observable in error metrics.

---

## TD-042: `_reconcile_account` does not query venue open orders absent from EventSpine

**Status**: Boot open-orders sweep RESOLVED in v0.84.0 for managed symbols; mainnet/shared-account hardening (account-wide no-symbol sweep, alert-and-block default, Class B verify-before-terminalize, WS unknown-order escalation) remains.
**Origin**: Round-18 codex-supervised audit (Pass 8)
**Severity**: Low (defense-in-depth; normal path appends `OrderSubmitIntent` before REST POST)
**Module**: `praxis/trading.py` (`_startup_account`, `_sweep_orphan_venue_orders`); `praxis/core/execution_manager.py:329-380` (`reconcile_orphan_commands`)

Boot reconciliation walks `trading_state.orders` (rebuilt from EventSpine) and queries the venue for each known order. It does NOT enumerate the venue's full open-order list (`query_open_orders`). `reconcile_orphan_commands` only flags `CommandAccepted`-without-followup. Combined, no path discovers an open venue order whose `OrderSubmitIntent` / `OrderSubmitted` was never appended to spine (e.g., SIGKILL between venue ACK and `event_spine.append`).

**Resolved in v0.84.0 (boot sweep)**: `_startup_account` now calls `_sweep_orphan_venue_orders(account_id)` after `_reconcile_account`. It queries `query_open_orders` for each managed symbol (`active_symbols(account_id) ∪ bootstrap_filter_symbols`) and, for any venue order whose `client_order_id` is not in `trading_state.orders` / `closed_orders`, logs a high-severity orphan event and cancels it — never adopting (Praxis cannot reconstruct `command_id` / `trade_id` / Nexus capital lineage from a venue order alone). The account is marked ready only if every orphan cancels; a cancel failure (or sweep error that cannot confirm orphans) leaves the account not-ready (fail closed, never trade alongside a live untracked order). This is the paper-soak policy: cancel-and-continue exercises recovery without human intervention.

**Remaining (mainnet / shared account)**: per-symbol sweeping derives symbols from local state, so it misses venue orders on untracked symbols. The items below are required before any deployment with manual order placement on the same account, a shared Binance account, or live trading.

**Acceptance addendum (codex-supervised audit re-run, 2026-05-04)**:
- **Boot-time open-order sweep**: in `_startup_account`, perform an account-wide open-order sweep BEFORE the user-stream open at `praxis/trading.py:312-318`. Sweeping after the WS opens leaves a window where venue events for an orphan `client_order_id` arrive at `_on_execution_report` before `trading_state.orders` is populated and get dropped at `praxis/trading.py:643-652`. The sweep must run early enough that any synthesized `OrderSubmitted` from a discovered orphan lands in `trading_state.orders` before WS events can reach `_on_execution_report`. The current `VenueAdapter.query_open_orders(account_id, symbol)` requires `symbol`; the fix must extend the contract to make `symbol` optional (Binance `GET /api/v3/openOrders` accepts no-symbol and returns the full account-wide list) so a single call returns every venue-side open order regardless of whether Praxis tracks the symbol. Per-symbol sweeping is insufficient because managed symbols are derived from local state and would miss venue orders on untracked symbols (which is exactly the manual/shared-account class this TD blocks). For each returned `VenueOrder` whose `client_order_id` is not in `trading_state.orders`: log at WARNING level, include `venue_order_id` + `client_order_id` + `symbol` + `qty` + `filled_qty` (the `VenueOrder` field names; `time_in_force` is not currently exposed on `VenueOrder`, so adding it to the alert payload requires extending the `VenueAdapter` / `VenueOrder` contract as part of the fix). Default behavior is alert-and-block (refuse to enter ready state); auto-cancel only behind explicit `--auto-cancel-orphan-venue-orders` flag.
- **Class B reconcile must verify before terminalizing**: `reconcile_orphan_commands` Class B path must call `query_order(account_id, symbol, client_order_id=client_order_id)` (account_id and symbol are reconstructable from the persisted `OrderSubmitIntent`) before emitting `_emit_orphan_rejection`. The recovery branch is selected on the returned `VenueOrder.filled_qty` and `VenueOrder.status` (Praxis-normalized `OrderStatus`: `OPEN` / `PARTIALLY_FILLED` / `FILLED` / `CANCELED` / `REJECTED` / `EXPIRED`); a missing-order response surfaces as `NotFoundError`:
  - `status == OPEN` and `filled_qty == 0`: synthesize `OrderSubmitted` (using venue-returned `venue_order_id`) instead of REJECTED; let `_reconcile_account` / WS handle from there.
  - `status == PARTIALLY_FILLED` (`filled_qty > 0`, still live): must NOT synthesize REJECTED — must reconstruct `OrderSubmitted` followed by one `FillReceived` per individual venue trade (fetched via `query_trades(account_id, symbol, start_time=intent.timestamp)` and filtered by `client_order_id`, mirroring the `_reconcile_fills` path at `praxis/trading.py:496-565`; the `start_time` window is bounded by the persisted `OrderSubmitIntent.timestamp`. Aggregating into a single `FillReceived` is incorrect because each event carries a unique `venue_trade_id` + per-fill fee fields and is deduplicated by trade ID in `EventSpine`) and emit a non-terminal PARTIAL `TradeOutcomeProduced`; the order remains live and `_reconcile_account` / WS handles subsequent fills and the eventual terminal status.
  - `status in {FILLED, CANCELED, EXPIRED}` with `filled_qty > 0`: must NOT synthesize REJECTED — must reconstruct `OrderSubmitted` followed by one `FillReceived` per individual venue trade (same `query_trades(account_id, symbol, start_time=intent.timestamp)` path as the PARTIAL branch above), then emit `TradeClosed` followed by the matching terminal `TradeOutcomeProduced` (FILLED / CANCELED / EXPIRED) to mirror the steady-state event order produced by `ExecutionManager._build_outcome` and `_build_abort_outcome` (`praxis/core/execution_manager.py:1440-1458, 1622-1641`). If reconstruction is infeasible (e.g. `query_trades` does not return the per-fill fee/commission detail from the executed batch), halt startup with operator-required reconciliation error rather than under-account the executed fills or skip the `TradeClosed` event.
  - `NotFoundError` raised, OR `status in {CANCELED, EXPIRED, REJECTED}` with `filled_qty == 0`: existing REJECTED synthesis is correct.
- **WS unknown-order escalation**: promote `praxis/trading.py` `_on_execution_report` unknown-`client_order_id` log from `_log.debug` to `_log.warning`. Add per-account `unknown_ws_orders_seen` counter for health metrics.
- **Coverage**: external venue order placed before boot → boot sweep alerts; Class B orphan with venue-confirmed-live → no REJECTED synth; Class B orphan with venue-confirmed-FILLED → recovery reconstruction or halt; WS executionReport for unseen `client_order_id` → warning + counter increment.
- **Promotion gate**: blocks any of unattended/multi-day paper trading, shared Binance account, manual/operator orders on the same account, resting LIMIT/STOP-heavy strategies, or live trading.

---

## TD-043: Cross-repo state mismatch (Nexus snapshot present, Praxis spine cleared) is not detected at boot

**Origin**: Round-18 codex-supervised audit (Pass 8)
**Severity**: Operator-only (manual state directory deletion required)
**Module**: `praxis/launcher.py:1389` (StateStore wiring); cross-repo: `nexus/startup/sequencer.py:358-484` (`_reconcile_capital`)

`EPOCH_ID` is a single env var shared across all accounts. If an operator deletes the Praxis SQLite DB but keeps Nexus snapshots, boot reconcile sees zero positions and clears Nexus's remembered positions; per-strategy risk fields keep their stale values. No assertion compares the Nexus snapshot's epoch to Praxis spine presence.

**When to fix**: When manual state-management workflows are formalized (runbook), or before adding a `--reset-state` operator flag.
**Migration**: Persist `epoch_id` in the Nexus snapshot. At boot, compare against Praxis spine's max event_seq presence; on disagreement, log a loud warning and require an explicit `--reset-state` flag before continuing. Belongs in the operator runbook regardless.

---

## TD-044: Shutdown EXIT submission silently fails if launcher asyncio loop has died before `_submit_exit`

**Origin**: Round-18 codex-supervised audit (Pass 9)
**Severity**: Low (requires loop-thread death scenario; graceful path is bounded)
**Module**: `praxis/launcher.py:1095-1097` (loop thread); cross-repo: `nexus/infrastructure/praxis_connector/praxis_outbound.py:74-100` (`send_command` via `run_coroutine_threadsafe`); `nexus/startup/shutdown_sequencer.py:434-442` (`_submit_exit` try/except)

`PraxisOutbound.send_command` uses `asyncio.run_coroutine_threadsafe(submit_command(...), loop).result(timeout=...)`. ShutdownSequencer's `_submit_exit` wraps it in try/except and logs on failure. If the launcher's asyncio loop is already dead by the time `_submit_exit` runs (e.g., loop thread aborted earlier in some failure path while nexus thread continues into shutdown), every shutdown EXIT silently fails. Final checkpoint still runs and persists state; venue orders may stay open until next boot's reconcile.

**When to fix**: When loop-thread failure modes are catalogued in operations, OR before adding any operator dashboard that surfaces "shutdown left orders open" as a metric.
**Migration**: Detect loop liveness in `_submit_exit` (e.g., `loop.is_running()`) and short-circuit to a queued local marker so the next boot's reconcile can pick up the dangling order; log loudly that the shutdown could not communicate with venue.

---

## TD-045: Symbol filters not loaded for fresh accounts; `_validate_order` fails open — RESOLVED

---

## TD-046: MARKET ENTER reservation lacks slippage buffer

**Origin**: Round-18 codex-supervised audit (Pass 10)
**Severity**: Low for liquid pairs (BTCUSDT testnet); Major for thin books or large notionals
**Module**: `praxis/launcher.py:540-579` (`_build_enter_context`)

For ENTER actions, `order_notional = action.size * reference_price` and `estimated_fees = order_notional * fee_rate`. The slippage estimate computed in `praxis/core/execution_manager.py:858` (`estimate_slippage(book, qty, side)`) is logged only — it does not feed back into reservation sizing. A high-slippage MARKET fill where `fill_notional > reservation_notional + reserved_fees` trips `INVARIANT_BREACH` in `CapitalController.order_fill`; `OutcomeProcessor` returns `success=False`, position state stays unmutated, capital reservation parked.

**When to fix**: Before deploying on illiquid pairs, OR if INVARIANT_BREACH on MARKET fills is observed in testnet.
**Migration**: Add a configurable slippage buffer (default ~50 bps) to the ENTER reservation: `order_notional = action.size * reference_price * (1 + slippage_bps / 10000)`. Or short-circuit MARKET ENTERs to use the slippage-estimated VWAP from `estimate_slippage` instead of `reference_price`.

---

## TD-047: No boot-time venue free-balance probe

**Origin**: Round-18 codex-supervised audit (Pass 10)
**Severity**: Low (operator misconfiguration only; first ENTER's REJECTED outcome surfaces it)
**Module**: `praxis/infrastructure/binance_adapter.py` (no balance API exposed); `praxis/launcher.py` (no balance probe at boot)

There is no `get_account_info` or balance-query method in `BinanceAdapter`, and no boot-time probe to confirm the account has enough USDT/BTC for the configured `capital_pool`. An operator misconfiguring credentials with empty testnet balance discovers this only after the first ENTER's `-2010 INSUFFICIENT_BALANCE` reject; strategies may keep retrying until rate-limited.

**When to fix**: When the operator runbook formalizes credential validation, OR before first multi-account paper trading (where the failure mode is harder to diagnose from logs).
**Migration**: At end of `_startup_account`, call a Binance `GET /api/v3/account` probe and warn if `free_quote_balance < capital_pool` for the account's quote asset. Optional gate on a `--require-balance` flag.

---

## TD-048: Command routing dicts are keyed by `command_id` only, not `(account_id, command_id)`

**Origin**: Round-18 codex-supervised audit (Pass 11)
**Severity**: Low (UUID4 collision probability ≈ 5×10⁻³⁷ at 1B items)
**Module**: `praxis/outcome_translator.py:104-105`; `praxis/core/execution_manager.py:139-143`

`OutcomeTranslator._state` and `_terminal_command_ids` are keyed by `command_id`. `ExecutionManager._accepted_commands`, `_terminal_commands`, `_commands`, `_aborted_commands`, `_command_trade_ids` likewise. `command_id = str(uuid.uuid4())` per `submit_command`. Cross-account collision is essentially zero today, but a future change to a deterministic-hash or human-readable ID would silently invite cross-account dispatch errors.

**When to fix**: Before any change to `command_id` derivation away from UUID4, OR alongside hardening defense-in-depth across registries.
**Migration**: Either (a) re-key the dicts as `dict[tuple[str, str], ...]` — `(account_id, command_id)` — or (b) add an architectural test asserting `command_id` is UUID4-shaped at every `submit_command` callsite.

---

## TD-049: No multi-account integration test asserts cross-account outcome routing isolation

**Origin**: Round-18 codex-supervised audit (Pass 11)
**Severity**: Low (current code is structurally sound; gap is test coverage only)
**Module**: tests (no existing two-account end-to-end test); production paths verified clean in audit

All multi-account assertions are static (uniqueness, dedup scope, epoch isolation, suffix collision). No test runs two Nexus instances concurrently with overlapping symbols and asserts that fills/outcomes are routed correctly per-account, capital/position state stays per-account, and the translator does not cross-contaminate. A future refactor of `_route_translated`, `_outcome_queues`, or translator state keys could silently cross-route outcomes without any test failure.

**When to fix**: Before any deployment with more than one Nexus instance per process, OR before any refactor of the outcome routing closures in the launcher.
**Migration**: Add an integration test that boots two Nexus instances against a shared ExecutionManager, drives outcomes for both accounts in interleaved order, and asserts each account's queue receives exactly its own outcomes and its OutcomeProcessor mutates only its own InstanceState.

---

## TD-050: EventSpine `account_id` is payload-only, not a column or index

**Origin**: Round-18 codex-supervised audit (Pass 11)
**Severity**: Low (no runtime corruption path observed; performance only)
**Module**: `praxis/infrastructure/event_spine.py:39-46` (events table schema); `praxis/trading.py:267-271` (replay reads then partitions in-memory)

The events table has no `account_id` column; the field lives only inside the orjson-serialized payload. `read(epoch_id)` returns ALL events for the epoch; `Trading.start` partitions in-memory by `event.account_id`. This is O(all rows) per-account-replay scan, and account routing trusts the deserialized payload. A wrong-account_id payload (programmer error or external corruption — SQLite cannot detect since payload is opaque) would route the event to the wrong account at replay.

**When to fix**: When per-account replay performance becomes load-bearing, OR before adding any database-level integrity tooling.
**Migration**: Add `account_id` as an indexed column on the events table. Per-account replay becomes O(rows-for-account). Existing rows would need a one-shot backfill from payload.

---

## TD-051: Launcher constructs `PlatformLimitsStageLimits()` with all-None defaults — operator-platform-caps are effectively disabled

**Origin**: Round-18 codex-supervised audit (Pass 12)
**Severity**: Major (operator safety caps designed in, not wired up; manifest `capital_pct` is the only ENTER cap)
**Module**: `praxis/launcher.py:371`; cross-repo: `nexus/core/validator/platform_limits_stage.py:115-208`

`platform_limits = PlatformLimitsStageLimits()` is constructed with no fields supplied — every operator cap (`max_order_notional`, `max_order_rate`, `max_position`, `max_daily_loss`, `max_capital_utilization`) defaults to None. The validator stage gates each check on `if limits.X is not None`, so all checks are skipped and the stage returns `allowed=True` unconditionally. A misconfigured strategy can submit an ENTER for the entire `strategy_budget` (or up to `capital_pool` if multiple strategies). The only safety net is per-strategy `capital_pct` budget computation in `CapitalController`.

**When to fix**: Before any deployment where operator caps must enforce per-order or per-day limits, OR before the next round of platform-limits configuration work.
**Migration**: Read `PlatformLimitsStageLimits` fields from manifest (or env vars) and populate at construction. Add a regression test asserting non-default limits flow through to the validator and reject ENTER appropriately.

---

## TD-052: Boot replay-from-spine for unconsumed `TradeOutcomeProduced` events — RESOLVED

---

## TD-053: HealthLoop demote to REDUCE_ONLY on sustained Conduit/Arrow feed staleness

**Origin**: Round-18 MAJOR-005 deferral (Praxis #86); reframed for the Conduit/Arrow feed after the Furnace-Conduit migration retired `MarketDataPoller`.
**Severity**: Major (defense-in-depth on top of validator PRICE-stage rejection)
**Modules**: `nexus/strategy/predict_loop.py`, `praxis/arrow_price_store.py`; cross-repo: `nexus/core/health_loop.py`, `praxis/core/domain/health_snapshot.py`

Freshness is enforced per call site after the migration: the Conduit `PredictLoop` skips a tick when `serving_manifest.generated_at` is stale, and `ArrowPriceStore.latest_close` returns `None` when the latest closed bar exceeds `max_staleness_intervals`, so `fallback_price_provider` / `mark_price_provider` yield `None` and the validator's PRICE stage rejects ENTERs cleanly. There is still no single system-wide signal: sustained Conduit/Arrow staleness does not demote `state.mode` to `REDUCE_ONLY` (EXITs allowed, ENTERs blocked) the way a venue-feed-degraded health gate would.

The current behavior is safe for paper trading (stale predictions are skipped; stale mark price rejects ENTER at PRICE stage). Mode demotion would add one coherent operator-facing signal instead of relying on per-call-site rejection.

**When to fix**: Before sustained mainnet operation, OR when a single operator-facing "feed degraded; trading reduced" signal is needed.

**Migration**:
1. Track consecutive stale/missing reads in the Conduit `PredictLoop` and/or `ArrowPriceStore` (per series); reset on a fresh read, increment on stale/absent.
2. Add a `feed_healthy: bool` field to `HealthSnapshot`; the launcher's health-snapshot callback samples the staleness counters and sets it.
3. In Nexus `HealthLoop` / `HealthEvaluator`, add a transition: `feed_healthy=False` to `REDUCE_ONLY`.
4. Test: simulate sustained stale Conduit manifest / Arrow frames so the snapshot reports unhealthy, HealthLoop demotes mode within the next tick, and the validator's MODE stage rejects ENTERs while EXITs still pass.

---

## TD-054: `Launcher._append_outcome_acked` synchronously blocks the Nexus thread on the Praxis loop

**Origin**: Greybeard pre-PR review of round-18 MAJOR-004 part B
**Severity**: Low at MMVP cadence; Major when Praxis loop overload becomes plausible
**Module**: `praxis/launcher.py:1199-1235` (`_append_outcome_acked`)

`_append_outcome_acked` is called from the `process_outcome` closure on the Nexus thread after `OutcomeProcessor.process` returns success. It dispatches the spine append onto the Praxis loop via `asyncio.run_coroutine_threadsafe(...).result(timeout=10)` — synchronous wait on the future. Under loop overload, every successful outcome incurs up to a 10s tax on the Nexus thread before the warning logs and outcome processing continues. There is no batching, no fire-and-forget option, and no metric. At MMVP cadence (~100 outcomes/day per account) this is invisible; on a degraded asyncio loop or a high-frequency strategy it becomes a real per-outcome stall.

**When to fix**: Before sustained mainnet operation, OR when an operator dashboard surfaces "OutcomeAcked latency" as a tracked metric.

**Migration**: Either (a) batch `OutcomeAcked` events and append asynchronously via a dedicated coroutine that the launcher schedules at startup, or (b) fire-and-forget the `run_coroutine_threadsafe` future without awaiting `.result()` and rely on the future's exception to log via `add_done_callback`. Option (b) is simpler and matches the "ack failure must not abort outcome flow" comment intent; the trade-off is the next-boot replay sees a brief window of acked-but-not-persisted outcomes that get redelivered (already idempotent on the Nexus side via the MAJOR-004 part A dedup).

---

## TD-055: `_rescue_by_client_order_id` returns `immediate_fills=()` even when the rescued order is FILLED / partially-filled

**Origin**: Copilot PR #87 review (round-18 MAJOR-002 follow-up)
**Severity**: Low under WS-healthy operation (the missed fill is reconciled by the next WS `executionReport`); Major if WS connection is broken at the moment of rescue or the venue's user-data stream lags
**Module**: `praxis/core/execution_manager.py:1196-1275` (`_rescue_by_client_order_id`); cross-call `praxis/infrastructure/binance_adapter.py:1338` (`query_trades`)

`_rescue_by_client_order_id` calls `query_order(client_order_id)` and returns `SubmitResult(immediate_fills=())` regardless of `venue_order.filled_qty` or `venue_order.status`. When `_post_order` is rescued from `OrderSubmitTimeoutError` / `DuplicateClientOrderIdError` and the venue had already executed fills before the response was lost, `_process_command` derives `filled_qty` solely from `result.immediate_fills` and emits the outcome as `PENDING` with `filled_qty=0`. Capital and position state stay un-credited until the next WS `executionReport` carrying those fills lands and the WS reconcile path catches up. If WS is disconnected or the user-data stream lags, the system can sit indefinitely with the venue holding live exposure that Praxis reports as zero-filled.

The current behavior is conservative — it does not lose state, it only delays correction — and the conservative-default reasoning is documented in the rescue docstring. But Copilot's point stands: the rescue path has a `filled_qty` signal in hand and discards it.

**When to fix**: Before sustained mainnet operation, OR before any deployment where the WS user-data stream has known reconnection gaps.

**Migration**: After the existing `query_order` succeeds with `venue_order.filled_qty > 0`, call `query_trades(account_id, symbol, start_time=cmd.created_at)` and filter to `vt.venue_order_id == venue_order.venue_order_id`. Map each `VenueTrade` to an `ImmediateFill` (`venue_trade_id`, `qty`, `price`, `fee`, `fee_asset`, `is_maker`) and pass the tuple as `SubmitResult.immediate_fills`. New failure modes to handle: (a) `query_trades` raises — fall back to the current `immediate_fills=()` behavior with a warning so the outcome path still emits a result, (b) `query_trades` returns fewer trades than `venue_order.filled_qty` implies (cumulative fills lag the order endpoint by one venue cycle) — emit what is available and log the discrepancy; the WS reconcile path will fill in the rest, (c) Binance returns trades for the wrong order due to a `client_order_id` collision — the `venue_order_id` filter prevents this, but tests should cover the empty-trades case explicitly.

Add tests covering: (1) rescue returns ImmediateFill tuple matching VenueTrade records when filled_qty > 0; (2) rescue returns empty tuple when filled_qty = 0 (no regression); (3) rescue falls back to empty tuple when query_trades raises VenueError; (4) rescue logs and emits empty tuple when query_trades returns zero records despite filled_qty > 0 (lag case).

---

## TD-056: `_ensure_entry_position` logs and skips when ref_price is None, allowing context-without-position if upstream PRICE gating regresses

**Origin**: Supervised audit (Pass 3) — paper-trade end-to-end audit
**Severity**: Low (defense-in-depth; gated upstream by validator PRICE stage)
**Module**: `praxis/launcher.py` (`_ensure_entry_position`); cross-repo: `nexus/infrastructure/praxis_connector/outcome_processor.py` (`_grow_position`)

`_ensure_entry_position` logs a warning and returns when `ref_price is None` (the existing docstring justifies this as "logging the skip rather than raising keeps the submitter loop alive" on a branch that the validator PRICE stage is supposed to make unreachable). The submitter then registers `command_contexts[command_id] = order_context` — `_build_order_context` does not depend on `ref_price`. When the ENTER FILL arrives, `_handle_fill` ENTRY path: `order_fill` mutates capital (succeeds because the TrackedOrder is in WORKING state), then `_update_position_on_fill` → `_grow_position` raises `RuntimeError('entry fill for missing position')`. `OutcomeLoop` catches the exception and logs it. Net result: capital incremented (in_flight → position_notional) but no `Position` record in `state.positions` → drift between capital aggregates and positions.

If an ENTER command is registered without a placeholder Position, a later ENTER fill can mutate `CapitalController` via `order_fill` and then raise in `_grow_position` because the position is missing. This leaves in-memory capital/position drift until restart. Today this is guarded by the validator PRICE stage (`_build_enter_context`'s no-price guard rejects the action before `_ensure_entry_position` runs), so the gap is defense-in-depth — only fires under a "deeper bug" path.

**Tradeoff to weigh before fixing**: the current `log and continue` behavior was intentional — the original author chose to keep the submitter loop alive on a "shouldn't happen" branch rather than crash it on a stale-data condition. Either resolution is defensible; pick one explicitly:

1. Make `_ensure_entry_position` fail the submit path when `ref_price is None` (raise / mark the action SUBMIT_FAILED so capital is released cleanly). Loses the loop-alive property; gains audibility on the upstream regression.
2. Keep the silent-skip in `_ensure_entry_position` but tighten the upstream guard so reaching this branch with `ref_price=None` becomes structurally impossible (e.g., an assertion in `_build_enter_context` that ENTER actions without ref_price never produce a granted CAPITAL decision). Preserves the current loop-alive property; relies on the upstream invariant.

**When to fix**: Before sustained multi-account or multi-strategy paper trading where any upstream regression in PRICE-stage gating would surface this drift, OR alongside any refactor of the validator PRICE stage.

**Migration**: Pick one of the two options above. Whichever way it goes, add a regression test that constructs an ENTER context with `ref_price=None` and asserts the failure mode the chosen option implies — either `submit_actions` returns SUBMIT_FAILED + capital released, OR `_build_enter_context` refuses to grant a CAPITAL decision in the first place.

---

## TD-057: Binance code -2010 is overloaded but `_post_order` treats every -2010 as `DuplicateClientOrderIdError`

**Origin**: Supervised audit (Pass 5) — paper-trade end-to-end audit
**Severity**: Low (functionally safe; ergonomics + wasted REST weight)
**Module**: `praxis/infrastructure/binance_adapter.py` (`_post_order` `OrderRejectedError` handler)

Binance documents venue code -2010 as `NEW_ORDER_REJECTED`, with the specific rejection reason carried in the response message string rather than encoded as a distinct numeric sub-code. Operationally the code is therefore message-overloaded — observed messages on this code include "Duplicate clientOrderId" and other order-rejection conditions whose exact catalog should be confirmed against the current Binance Spot REST error reference before fixing. The current code wraps ALL `OrderRejectedError(venue_code=-2010)` as `DuplicateClientOrderIdError` based on the venue code alone, ignoring the message string. The rescue path then queries the venue for `client_order_id`; if no order was created (the non-duplicate case), `query_order` returns `NotFoundError` → rescue returns None → `_record_submit_failed` → REJECTED outcome carrying a misleading "duplicate clientOrderId" reason instead of the actual venue message.

Functionally safe: capital still released, outcome correctly REJECTED, dedup intact. Two costs: (1) wasted `query_order` REST weight for every non-duplicate -2010 — irrelevant at MMVP rate, observable at high cadence; (2) the REJECTED outcome's `reason` string says "duplicate clientOrderId" when the venue actually meant something else, making operator forensics harder during incident triage.

**When to fix**: Before sustained mainnet operation, OR when operator-facing reason strings become load-bearing for incident triage.

**Migration**: First, sample real `-2010` responses against the Binance Spot REST testnet (or pull the canonical message catalog from the current Binance error reference) to confirm which messages are actually emitted and which are duplicate-clientOrderId. Then discriminate `-2010` by venue message in `_post_order`. Only duplicate-clientOrderId messages should raise `DuplicateClientOrderIdError`; other `-2010` responses should remain plain `OrderRejectedError` with the original reason preserved. Implementation options: (a) substring check on `exc.reason` for the confirmed duplicate-clientOrderId fragment before wrapping; (b) maintain a small lookup table keyed on canonical venue-message fragments. Option (a) is simpler; option (b) is more durable against Binance message-wording changes. Add tests covering `-2010` with the confirmed duplicate-clientOrderId message (rescue) and `-2010` with each other observed variant (REJECTED with original reason, no rescue).

---

## TD-058: No end-to-end crash-window recovery harness

**Origin**: Supervised audit (Pass 6) — paper-trade end-to-end audit
**Severity**: Low (test gap, not a runtime defect)
**Module**: `tests/` across both repos (Praxis + Nexus); cross-cutting recovery contract

Current recovery guarantees are covered by unit/component tests (orphan reconcile, OutcomeAcked gate, WAL torn-tail, replay idempotency, boot reconciliation), but no test kills the process between key durability boundaries and verifies restart behavior end to end. Future regressions in EventSpine ordering, OutcomeAcked gating, Nexus WAL persistence, or boot reconciliation could pass unit tests while breaking the cross-repo recovery chain. Detection deferred to operator forensics during paper-trade run.

The crash windows that need coverage (per Pass 6 matrix):

1. After `CommandAccepted`, before `OrderSubmitIntent` (Class A orphan recovery).
2. After `OrderSubmitIntent`, before REST POST (Class B orphan recovery).
3. After REST accepted, before `OrderSubmitted` (TD-042 ghost-order risk).
4. After `OrderSubmitted`, before `TradeOutcomeProduced` (Praxis `_reconcile_account` flow).
5. After `TradeOutcomeProduced`, before Nexus callback (TD-052 latent gap).
6. After Nexus mutation, before `append_mutation` (TD-086 dedup-after-mutation gap).
7. After `append_mutation`, before `OutcomeAcked` (TD-052 + TD-086 double-mutation hazard).
8. After `OutcomeAcked`, before final checkpoint (FINAL-TD-01/02 derivation paths).
9. During final checkpoint (FINAL-MAJOR-04 atomic WAL).

**When to fix**: Alongside TD-052 implementation (a TD-052 boot-replay producer needs the crash-window harness to verify acceptance), OR before any Praxis/Nexus refactor that touches EventSpine or `state_store` and would benefit from a regression guard on the cross-repo recovery contract.

**Migration**: Build a crash-window integration harness covering at least the nine boundary types above. For each window: spin up a Praxis launcher with both repos wired, drive it to the boundary state via deterministic test inputs, simulate process kill (e.g., raise `KeyboardInterrupt` mid-flight or use `os.kill(pid, SIGKILL)` in a subprocess), then restart with the same state directory and assert the recovery contract (capital aggregates correct, no double-mutation, no stranded orders, no stale risk gates). Place harness in either repo (the recovery flow spans both); cross-reference the other repo's TD entry. Recommended location: a new `tests/integration/crash_recovery/` directory in Praxis since the launcher orchestrates the cross-repo boot.

---

## TD-059: `BinanceUserStream._clean_setup_connection` leaks freshly-opened ws on `CancelledError`

**Origin**: Greybeard pre-PR review (fix/binance-ws-api-user-data-stream)
**Severity**: Low (resource leak, not correctness)
**Module**: `praxis/infrastructure/binance_ws.py:_clean_setup_connection`

Between `await session.ws_connect(ws_api_url)` and the success-path assignment `self._ws = ws`, a `CancelledError` raised by `close()` cancelling `_reconnect_task` is not handled by the `except (aiohttp.ClientError, TimeoutError, VenueError):` block. The freshly-opened `ws` therefore goes out of scope without an explicit `await ws.close()`. The asyncio garbage collector will eventually destroy the `ClientWebSocketResponse`, but until then the socket and the underlying TCP connection are held open. Pre-existing pattern from the listen-key-era code; the WS-API rewrite preserves it rather than introduces it.

**When to fix**: When sustained reconnect activity on a long-lived paper-trade run produces observable file-descriptor or connection-pool exhaustion in operator metrics, OR when the next refactor of `_clean_setup_connection` happens for any other reason.

**Migration**: Replace the bare `except (aiohttp.ClientError, TimeoutError, VenueError):` with a `try/finally` that closes the local `ws` whenever `self._ws` was not assigned the new value, OR add `BaseException` to the except tuple and re-raise. The `try/finally` shape is preferred since it also covers the `_subscribe` happy path where the publisher goes away mid-call.

---

## TD-060: `MarketDataPoller` test cleanup not protected by `try/finally` — OBSOLETE (superseded by Conduit migration)

---

## TD-061: Synchronous Limen + binancial fetches block `Launcher.launch()` for minutes — OBSOLETE (superseded by Conduit migration)

---

## TD-062: `_aggregate_spot_klines` is a private Limen helper that Praxis depends on — OBSOLETE (superseded by Conduit migration)

---

## TD-064: `binsim` `POST /api/v3/order` does not enforce its own `exchangeInfo` LOT_SIZE / PRICE_FILTER / NOTIONAL filters

**Severity**: Medium (only one caller today, but shape inconsistency)
**Module**: `praxis/binsim/server.py:_submit_order` (introduced by Vaquum/Praxis#112)

`GET /api/v3/exchangeInfo` declares filters (`PRICE_FILTER.tickSize=0.01`, `LOT_SIZE.stepSize=1e-5`, `LOT_SIZE.minQty=1e-5`, `LOT_SIZE.maxQty=9000`, `NOTIONAL.minNotional=5`) but `POST /api/v3/order` accepts any positive `quantity` and walks the book directly. Real Binance rejects sub-minQty orders with code `-1013` ("Filter failure: LOT_SIZE"); binsim silently fills. Today the only caller is Praxis's `BinanceAdapter`, which runs `_validate_order` BEFORE the POST (`binance_adapter.py` `~1100`), so the gap is unreachable through normal use. Any other client that talks to binsim directly would observe the inconsistency.

**When to fix**: When binsim grows a second client (e.g. a paper-trade smoke runner that doesn't share `BinanceAdapter`'s validation), or before promoting binsim from "paper trading" to "shared dev sandbox".

**Migration**: In `_submit_order`, after parsing `qty`, snap it against `_FILTERS_PAYLOAD['filters']` (same dict the GET serves) and reject with `400` + Binance code `-1013` if `qty < minQty`, `qty > maxQty`, `(qty / stepSize) != round(qty / stepSize)`, or `qty * walk_price[0] < minNotional`. Mirror Binance's exact error message format so adapter-side error mapping needs no changes.

---

## TD-065: `binsim` taker fee rate is hardcoded process-wide, not per-account

**Severity**: Low (spec gap; correctness is identical if all accounts use the same rate)
**Module**: `praxis/binsim/server.py:_TAKER_FEE_RATE` (introduced by Vaquum/Praxis#112)

`_TAKER_FEE_RATE: Final[Decimal] = Decimal('0.001')` is a module-level constant. Every order across every binsim account pays the same 10bps. The original issue #112 spec said fees are "configurable per account, fee asset = quote (USDT) by default"; the MMVP collapsed that into a single constant because all current paper accounts on a given binsim deployment share the same fee tier anyway. The Ledger's `apply_order` already accepts pre-computed per-fill fees, so the change is HTTP-handler-local.

**When to fix**: When binsim is shared across paper accounts that have different real-world fee tiers (e.g. VIP-9 strategist account + retail demo account on the same binsim).

**Migration**: Promote `Ledger.Account` to carry a `fee_rate` field, set by `register_account` (new arg with a 10bps default). `_submit_order` resolves the account from `X-MBX-APIKEY` via `Ledger.account_for_api_key`, looks up the account's `fee_rate`, and uses it for the per-level commission instead of the module constant.

---

## TD-066: `binsim` `Ledger.Account.seen_client_order_ids` grows without bound

**Severity**: Low (asymptotic; current deployments are short-lived)
**Module**: `praxis/binsim/ledger.py:Account` (introduced by Vaquum/Praxis#112)

`seen_client_order_ids: set[str]` is the dedup index for `apply_order`. It is persisted in the snapshot as `sorted(account.seen_client_order_ids)`. Every successful order adds one element; the set is never pruned. Every successful order also triggers a snapshot rewrite of the entire account (balances + fills + seen_client_order_ids), so the snapshot write is O(N+M) where N = lifetime fills and M = lifetime seen_cids. For a paper account doing 100 orders / day that's ~36,500 set elements per year — well within the realm of working comfortably but growing.

Binsim restarts reset state only if the operator wipes `BINSIM_STATE_DIR`; the default behavior is to persist across restarts, so the set really does accumulate across the lifetime of a binsim deployment. The Praxis launcher's EPOCH_ID concept (which RESETS Praxis-side state when bumped) does not propagate to binsim — binsim has no notion of epochs.

**When to fix**: When the snapshot write latency becomes observable in operator dashboards (probably ~10⁵ orders), or when binsim is promoted to a longer-lived per-strategist environment.

**Migration**: Either (a) cap the set at the last N client_order_ids (FIFO eviction), or (b) introduce a TTL keyed on the recorded fill's timestamp. Option (a) is simpler; pick N large enough to outlast any reasonable Praxis-side retry window (~10⁴ is safe). For (b), Binance itself dedupes client_order_ids only within a recent window (the exact value isn't public; we'd pick something like 24h based on Praxis's own command lifecycle).

---

## TD-067: No Praxis-side integration test for YAML-backed SFD bundle launch path

**Severity**: Low (regression would surface at deploy, not at unit-test time)
**Module**: `praxis/launcher.py` + `tests/test_launcher_sfd_path.py` (gap surfaced by Copilot on Vaquum/Praxis#117)

Praxis ships `tests/test_launcher_sfd_path.py` (91 lines) that pins the sys.path management at `praxis/launcher.py:874` (`_ensure_strategies_path_importable`) — but that helper is only relevant for the **legacy Python-module SFD path** where `Limen.Trainer.__init__` calls `importlib.import_module(metadata['sfd_module'])` to reload the SFD class from a user file on disk.

The YAML-based SFD path enabled by the `vaquum_limen v3.0.6 → v3.9.0` bump in Praxis v0.64.0 (and the matching Nexus v0.49.0 → v0.50.0 bump from Vaquum/Nexus#70) bypasses that helper entirely: bundles declare `metadata.json["sfd_module"] = "yaml:<name>"` and Limen's [`limen/yaml/`](https://github.com/Vaquum/Limen/tree/v3.9.0/limen/yaml) pipeline resolves files (`<name>.json`, `manifest.yml`, `round_data.jsonl`, `results.csv`) from `experiment_dir` directly — no `sys.path` mutation, no `importlib.import_module` call. So the existing Praxis launcher SFD test cannot regress on YAML loading; there is no symmetric Praxis-side regression guard.

The architectural reality is that the meaningful YAML-bundle regression coverage already lives upstream in two places: Limen's [`tests/test_yaml.py`](https://github.com/Vaquum/Limen/blob/v3.9.0/tests/test_yaml.py) (975 lines pinning the YAML loader internals — parser, compiler, resolver, validator, rules) and Nexus's [`tests/test_limen_trainer_contract.py`](https://github.com/Vaquum/Nexus/blob/6d6af6056567e1571ad2353ec660b89283474e50/tests/test_limen_trainer_contract.py) (10 cases pinning the `Trainer.__init__(experiment_dir, data=None)` + `Trainer.train(permutation_ids)` public surface). A future Limen/Nexus pin bump that regresses YAML loading would still be caught by those upstream test suites before merge into Praxis — but the failure mode the Copilot bot raised is real: a Praxis-side test would catch it specifically through the Praxis launcher boot path, where the deployment actually fails.

The blocker for landing the test now is fixture cost. A minimal valid Limen v3.9.0 YAML SFD bundle requires `metadata.json` (with `sfd_module: "yaml:<name>"`, `limen_version`), `<name>.json` (data source + uel_run config), `manifest.yml` (complete enough to compile into a `Manifest` with `manifest()` + `params()` — at minimum: `data_source`, `split_config`, `features`, `target`, `scaler`, `architecture`), and `round_data.jsonl` (at least one round with populated `round_params`). The downstream artifact this pin bump unblocks (`btc_logreg_15m_up_early__r0024`) ships with `limen_version: "3.9.2"` — an unreleased Limen dev version — so building a Praxis-side fixture against a frozen-in-time schema risks coupling the test to a moving target.

**When to fix**: When the experiment_runner bundle format stabilizes (i.e. the next experiment_runner release ships against a tagged Limen version, not a dev build), OR when the next YAML-bundle deploy lands (so the fixture can be a copy of a real production bundle with parameter values redacted). Whichever comes first.

**Migration**: Add `tests/test_launcher_yaml_sfd_path.py` symmetric to `test_launcher_sfd_path.py`. The test should:
1. Stage a minimal YAML SFD bundle in `tmp_path` (`metadata.json`, `<name>.json`, `manifest.yml`, `round_data.jsonl`) — extract the fixture from a known-good production bundle and prune to the minimum the Trainer accepts.
2. Boot the launcher path through `Launcher._build_nexus_runtime` (or its successor) with a manifest YAML pointing at the staged experiment_dir.
3. Assert (a) the launcher does NOT raise the v3.0.6-era `ValueError: sfd_module 'yaml:...' is not a dotted sequence of valid Python identifiers` (the canonical regression marker), and (b) the resulting `Trainer` instance has a non-None `_manifest`, confirming YAML dispatch reached the loader.
The test should NOT exercise `train()` — that's covered upstream — only the `Trainer.__init__` → `_load_sfd_module` → YAML-dispatch path that's Praxis's interest.

---

## TD-068: Old per-account / superseded-epoch state dirs are never reaped

**Severity**: Low (disk accumulation only; no correctness impact)
**Module**: `praxis/launcher.py:2052` (surfaced by Greybeard pre-PR review on the Vaquum/Praxis#120 fix)

After v0.66.0 folded `EPOCH_ID` into the InstanceState path (`STATE_BASE / <account_id> / <epoch_id>`), every superseded epoch's tree (`snapshots`, `wal`, and — when `STRATEGY_STATE_BASE` is unset — `strategy_state`) plus the legacy account-level dir left by pre-v0.66.0 deploys (`STATE_BASE / <account_id>/…`) stays on disk untouched. When `STRATEGY_STATE_BASE` is set, strategy state lives under its own epoch tree (`STRATEGY_STATE_BASE / <account_id> / <epoch_id>`) and accumulates there independently. Each epoch bump creates a new `…/<epoch_id>/` tree and never reaps the prior one, so a long-lived host with frequent epoch bumps accumulates dead state indefinitely. No correctness impact — `recover()` only reads the current epoch's path, so stale dirs are inert.

**When to fix**: When deployment cadence makes the accumulation material on a long-lived host, or as part of any state-retention/cleanup policy work.

**Migration**: Add a boot-time or scheduled sweep that removes, for epochs `e < current` (retain the prior 1–2 for forensic rollback): `STATE_BASE / <account_id> / <e>`, `STRATEGY_STATE_BASE / <account_id> / <e>` when `STRATEGY_STATE_BASE` is set, and the legacy account-level `STATE_BASE / <account_id>/{snapshots,wal,strategy_state}` left by pre-v0.66.0 deploys. Gate the sweep on an explicit retention count so a misconfigured `EPOCH_ID` cannot wipe the active tree.

## TD-069: `MtmLoop` `mark_price_provider` aborts the entire tick on any non-BTCUSDT symbol

**Origin**: Greybeard pre-PR review of `chore/bump-nexus-0.54.0-and-wire-schedulers` (v0.69.0 scheduler wiring)
**Severity**: Low today (only BTCUSDT deployments shipped; the codebase carries `_DEFAULT_SYMBOL = 'BTCUSDT'` assumptions in many sites). Becomes a correctness blocker the day a manifest adds a second symbol.
**Module**: [`praxis/launcher.py`](praxis/launcher.py) `_build_nexus_runtime`'s `mark_price_provider` closure

The MTM `mark_price_provider` wraps the existing [`_last_close_from_poller`](praxis/launcher.py) which only knows about `BTCUSDT`. To preserve the strict-no-partial-writes contract on `MtmLoop`, the provider returns `None` for any other symbol; `MtmLoop` interprets `None` as "mark unavailable for this symbol" and aborts the entire tick without writing any unrealized P&L for any position (per [`mtm_loop.py:189-203`](https://github.com/Vaquum/Nexus/blob/bd61a0a60eefe8c55ef43719c72081193f66e097/nexus/core/mtm_loop.py) "stale marks are preferred over half-marked snapshots"). The day a manifest adds a non-BTCUSDT sensor that opens a position, every MTM tick will silently abort for the BTC positions too, leaving the open book unmarked indefinitely — risk gates running blind to the open book, exactly the failure mode Nexus #76 + Praxis v0.69.0 just closed.

The only operator signal will be a per-tick WARN log (`MtmLoop: mark price unavailable; tick aborted`) emitted from inside Nexus; nothing in Praxis surfaces it as a metric or health-loop alert.

**When to fix**: Before any deployment that adds a manifest entry for a symbol other than BTCUSDT. Catches forward-looking — the day this matters, the system silently degrades.

**Migration**: Extend [`MainCache`](praxis/market_data_cache.py) and [`_last_close_from_poller`](praxis/launcher.py) (and downstream the Limen bundle layer + `_DEFAULT_SYMBOL` usage in [`praxis/launcher.py`](praxis/launcher.py)) to be per-symbol-keyed rather than BTCUSDT-only. Concretely: replace `_last_close_from_poller(self._poller, kline_sizes)` with a per-symbol lookup `self._poller.get_last_close(symbol, kline_size)` and either (a) wire a `symbol_to_kline_size` map from the manifest so the MTM provider can resolve symbol → kline → last close, or (b) standardise on a single kline size for MTM (e.g. 60s) and key purely by symbol. The MTM provider then returns the per-symbol last close instead of `None`, and `MtmLoop` ticks proceed for any subset of symbols that have a fresh cache entry. The "abort on `None`" semantics is still correct for any symbol whose cache is empty / stale — it's the silent BTCUSDT-only fallback that's the issue.

A defensive intermediate: add a per-account or boot-time assertion that every symbol referenced by the manifest's wired sensors is in `kline_sizes` AND has a working last-close lookup; refuse to boot otherwise. Catches the misconfiguration loudly rather than letting it surface as a slow degradation in MTM.

## TD-070: `DepthPoller` success diagnostic logs at INFO on every poll

**Origin**: Greybeard pre-PR review of `feat/binsim-depth-replica-guards` (v0.70.0 binsim depth-replica guards)
**Severity**: Low — operationally noisy but not a correctness issue
**Module**: [`praxis/binsim/feed.py`](praxis/binsim/feed.py) — the `_log.info('depth poll succeeded', ...)` block after `book.replace` in `poll_once`

The per-poll INFO diagnostic added in v0.70.0 fires on every successful upstream poll, so the binsim container log gains roughly `86,400 lines/day` at the default `BINSIM_POLL_INTERVAL_MS=1000` cadence. The volume is what the post-mortem-visibility goal required — operators need a continuous timeseries of what binsim was serving to reconstruct future incidents — but error/anomaly-only logging would carry the bulk of the diagnostic signal at ~1% of the line volume, and the persistent volume bumps the container's `json-file` log driver through its `max-size=50m`, `max-file=5` rotation window faster than the underlying app events do.

**When to fix**: When the binsim log volume starts displacing useful Praxis logs in the rotated tail (i.e. when a post-mortem opens and the relevant Praxis events have already aged out because binsim depth lines pushed them past the 5×50MB window), OR when a metrics path lands and the per-poll snapshot can be emitted as a metric instead of a log line.

**Migration**: Either (a) downgrade the per-poll log to DEBUG and add a once-per-N-polls INFO heartbeat (where N is env-tunable, e.g. `BINSIM_DEPTH_LOG_INTERVAL_POLLS=60` for one INFO line per minute at the 1Hz default) — preserves operator visibility at 1.6% of the current volume, or (b) emit the per-poll snapshot as a structured metric (Prometheus / statsd / OTLP) and drop the diagnostic log entirely, letting the metrics path carry the timeseries. (b) is the cleaner long-term solution but requires a metrics dependency the binsim does not currently have.

## TD-071: `DepthPoller` magnitude floor uses one symmetric threshold for ask AND bid

**Origin**: Greybeard pre-PR review of `feat/binsim-depth-replica-guards` (v0.70.0 binsim depth-replica guards)
**Severity**: Low today (current upstream + buy-only deployment have asymmetric tolerance for bid-side thinness), elevated the day either condition changes
**Module**: [`praxis/binsim/feed.py`](praxis/binsim/feed.py) — the `if ask_depth < self._min_top20_depth_btc or bid_depth < self._min_top20_depth_btc:` check in `poll_once`

The magnitude floor applies `min_top20_depth_btc` to both `ask_depth` and `bid_depth` with `or`. The live upstream mirror shows a persistent ask/bid asymmetry — observed at `5.64 BTC ask top-20` vs `0.41 BTC bid top-20` during the v0.70.0 work — and the current deployment is buy-only (sells only on exit), so ask-side thinness is the operational risk and bid-side thinness is mostly cosmetic. With one symmetric threshold any future tightening of `BINSIM_MIN_TOP20_DEPTH_BTC` past the current bid-side depth (e.g. raising the floor to 0.5 BTC) would force every poll to reject on the bid side even when the ask side — the side actually walked by every buy entry order — is healthy.

**When to fix**: When the operational depth floor needs to be raised past the upstream's typical bid-side depth (i.e. when a future incident reveals ask-side thinness in the `0.05 – 0.5 BTC` range that the current floor misses, AND raising the floor would symmetrically reject every normal bid snapshot), OR when the deployment adds a sell-side strategy that materially depends on bid liquidity.

**Migration**: Split the single threshold into two:
- `min_top20_ask_depth_btc` + `min_top20_bid_depth_btc` poller fields, with env vars `BINSIM_MIN_TOP20_ASK_DEPTH_BTC` and `BINSIM_MIN_TOP20_BID_DEPTH_BTC`.
- Both default to `min_top20_depth_btc` (for backward compatibility — the existing single env var stays the "set both" knob, the new ones override per side).
- The startup log surfaces all three values so an operator can see whether they configured asymmetric thresholds.
- The rejection log already includes per-side `ask_top_n_qty` / `bid_top_n_qty` so operators can already see which side tripped; the migration only adds per-side configurability, not per-side diagnostics.

## TD-072: REMOVED — addressed in PR [#131](https://github.com/Vaquum/Praxis/pull/131) round-1 review

Originally deferred during the v0.71.0 pre-PR Greybeard pass: the three `MATERIALIZED toDecimal128OrZero` columns silently coerced missing/malformed values to `0`. Copilot review of PR #131 overruled the deferral and the schema was switched to `Nullable(Decimal(38, 18))` + `toDecimal128OrNull` before merge (cash-flow panel updated to `coalesce(col, 0)` so the Nullable change doesn't propagate NULL through downstream arithmetic). No latent debt remains; this section is retained as a historical marker so future readers do not re-issue the same TD number.

## TD-073: `spine_mirror` reuses a single `clickhouse_connect` client across the entire process lifetime without explicit reconnection

**Origin**: Greybeard pre-PR review of `feat/observability-grafana-stack` (v0.71.0 observability stack)
**Severity**: Low (`clickhouse_connect` documents internal connection-pool reconnection on transport failures; observed in prod-equivalent staging that a ClickHouse restart does not stall the mirror), elevated if a future driver version drops the auto-reconnect guarantee
**Module**: [`observability/spine_mirror.py`](observability/spine_mirror.py) `main()` — `ch = clickhouse_connect.get_client(...)` called once at startup, then reused for every tick's `query` + `insert` for the process lifetime

The `clickhouse-connect` client is created exactly once in `main()` and never re-created. The library claims internal reconnection on broken-pipe / connection-reset, but the claim is not verified end-to-end against a `docker restart praxis-clickhouse`. Until the verification exists, a future driver bump or a corner-case transport failure could leave the mirror running with a permanently-dead client; the only signal would be every tick logging the same connection error and the backoff continuing forever.

**When to fix**: When either (a) a real ClickHouse restart on prod-equivalent reveals the mirror gets stuck, or (b) the `clickhouse-connect` dep is bumped to a version that does not document auto-reconnect.

**Migration**: Wrap the client in a tiny `_ClientHolder` that rebuilds on consecutive `OperationalError` count crossing a threshold (e.g. 3), with a structured log entry on each rebuild. Alternative: add an explicit healthcheck on the spine-mirror container that pings ClickHouse independently and lets `restart: unless-stopped` restart the whole process on persistent failure — heavier but uses Compose's existing supervision.

## TD-074: `praxis-spine-mirror` waits only for ClickHouse `service_started`, not `service_healthy`

**Origin**: Greybeard pre-PR review of `feat/observability-grafana-stack` (v0.71.0 observability stack)
**Severity**: Low — currently survives the cold-start race via the mirror's `_RECOVERABLE_ERRORS` retry loop with exponential backoff; if `clickhouse_connect.get_client` or `_ensure_schema` raises during cold-start, the call site goes through `_backoff_seconds(consecutive_failures)` (doubling from 1s, clamped at 300s) and retries on the next iteration
**Module**: [`observability/docker-compose.observability.yml`](observability/docker-compose.observability.yml) — `praxis-spine-mirror.depends_on.praxis-clickhouse.condition: service_started` (and the same value on `praxis-grafana`)

Compose's `service_started` condition fires when the container is up, not when ClickHouse's HTTP listener is accepting queries. The mirror's first-tick `_ensure_schema` race against ClickHouse boot is currently handled by the mirror's recoverable-error retry loop (TD-073 sibling), and Grafana's datasource provisioning happens lazily on first dashboard request so the same race is invisible. The mode is "works via retry"; a healthcheck-gated path would be "works by waiting".

**When to fix**: When either (a) the stack is composed with strict-mode supervisors that flag the cold-start error logs as a regression, or (b) a future ClickHouse upgrade meaningfully slows boot past the mirror's backoff envelope.

**Migration**: Add a `healthcheck` block to `praxis-clickhouse` (`test: ["CMD", "wget", "--no-verbose", "--tries=1", "--spider", "http://localhost:8123/ping"]`, `interval: 5s`, `timeout: 3s`, `retries: 10`) and flip both consumers' `condition` to `service_healthy`. The mirror's retry loop stays as defense-in-depth.

## TD-075: `praxis-spine-mirror` bind-mounts a hardcoded `/opt/praxis/state` host path

**Origin**: Greybeard pre-PR review of `feat/observability-grafana-stack` (v0.71.0 observability stack)
**Severity**: Low — operationally limiting, not a runtime defect; any host that puts Praxis state somewhere other than `/opt/praxis/state` (dev laptop, integration test rig, future multi-tenant deployment) needs an edit to the committed compose file
**Module**: [`observability/docker-compose.observability.yml`](observability/docker-compose.observability.yml) `praxis-spine-mirror.volumes` — `- /opt/praxis/state:/spine:ro`

The bind-mount source is a hardcoded host path. The deployment convention happens to be `/opt/praxis/state` and the rest of the Praxis launcher / state-store code shares that assumption, but the observability stack is the only Praxis surface that wires it in via a Compose file. A future move to `/var/lib/praxis` / per-tenant subdirs / a CI rig at `/tmp/praxis-test-state` requires editing the committed file rather than overriding an env var.

**When to fix**: When the first non-default Praxis host needs to run the observability stack, OR when the launcher's `PRAXIS_STATE_DIR` env var (TD-001 lineage) lands and the operator wants the observability mount to follow the same knob.

**Migration**: Replace the volume entry with `- ${PRAXIS_STATE_DIR:-/opt/praxis/state}:/spine:ro` and document the `PRAXIS_STATE_DIR` knob in [`observability/.env.example`](observability/.env.example). The default keeps existing deployments working without action.

## TD-076: REMOVED — addressed in PR [#131](https://github.com/Vaquum/Praxis/pull/131) round-6 review

Originally deferred during the v0.71.0 pre-PR Greybeard pass: `observability/spine_mirror.py` had no automated test coverage. Copilot review of PR #131 overruled the deferral and the test suite was added before merge: [`tests/test_spine_mirror.py`](../tests/test_spine_mirror.py) (36 cases) covers `_parse_ts` across 6 timestamp shapes, `_backoff_seconds` monotonicity + clamp, `_to_rows` bytes/str/invalid-utf8 round-trip + integer coercion, `_current_cursor` empty-table/NULL/populated paths with mocked client, `_IDENTIFIER_RE` positive (6 safe names) + negative (10 unsafe names including hyphen/space/semicolon/SQL-injection shapes), and `_ensure_schema` issues the correct `CREATE DATABASE` + `CREATE TABLE` statements against the supplied database name. No latent debt remains; this section is retained as a historical marker so future readers do not re-issue the same TD number.

## TD-077: `_build_*_context` reserves against un-snapped `cmd.qty` on a filter-cache miss

**Origin**: Greybeard pre-PR review of `fix/cmd-qty-stepsize-presnap` (v0.72.0 qty pre-snap fix)
**Severity**: Low — narrow cold-start window only (between `BinanceAdapter.__init__` and the first `get_exchange_info` round-trip landing in `self._filters`); the existing submit-time `_snap_qty_to_lot_step` snaps the venue request down before submission, so the only consequence is an off-by-up-to-`lot_step × reference_price` reservation that the next `order_fill(terminal=True)` (Nexus v0.55.0) releases anyway. Net: a few cents of phantom-reserved capital for the duration of one fill cycle on cold start, gone after the first round-trip closes.
**Module**: [`praxis/launcher.py`](../praxis/launcher.py) `_build_enter_context` + `_build_exit_context` — the `if venue_adapter is not None:` block. [`praxis/infrastructure/binance_adapter.py`](../praxis/infrastructure/binance_adapter.py) `quantize_for_command` — the `filters is None` branch returns `CommandQuantization(snapped_qty=qty, rejection_reason=None)` unchanged.

On cold start, `BinanceAdapter._filters` is empty until the first `get_exchange_info` call lands. During this window, `quantize_for_command(symbol, qty, ...)` returns the input `qty` unchanged — the launcher computes `order_notional = unsnapped_qty * reference_price`, capital is reserved against that figure, then `submit_order` snaps the actual venue request down to `lot_step` via `_snap_qty_to_lot_step`. The reservation is therefore off by up to one `lot_step × reference_price` (e.g. `0.00001 BTC × $80k = $0.80`) until the order completes and the residual gets released by the Nexus v0.55.0 terminal-release path. The mismatch is bounded, transient, and cancels on close — but a reader of `quantize_for_command` could miss that the "pass-through on cache miss" branch silently delivers an un-snapped qty into the validator.

**When to fix**: When either (a) the launcher boot sequence is reworked to require `get_exchange_info` succeeding before `start_dispatch` (so the cold-start window stops existing), OR (b) an incident traces back to a reservation-vs-actual mismatch on the first few orders after a fresh boot.

**Migration**: Two options. (i) In `quantize_for_command`, treat `filters is None` as `INTAKE_FILTERS_NOT_CACHED` rejection — the launcher then drops the action and waits for the next cycle once `exchangeInfo` lands. Conservative; eats a few seconds of initial throughput on every cold start. (ii) In `Launcher.start`, gate `start_dispatch()` on a `await venue_adapter.get_exchange_info()` round-trip before opening the strategy event loop. Adds 100-200ms to cold-start; eliminates the window entirely. Option (ii) is cleaner and matches what `BinanceAdapter` already does for the WS keepalive boot sequence.

## TD-078: `estimate_slippage` is observation-only — no execution guard rejects bad-fill MARKET orders

**Origin**: Architectural review during v0.72.0 monkeypatch + codex round-3 design discussion (200 bps buffer hack)
**Severity**: Low under current scope (BTCUSDT-only, $5–50 per order; BTC top-of-book on Binance routinely has $100k+ within a cent of mid so walking the book costs essentially top-of-book price). Elevated if order sizing scales by 1–2 orders of magnitude, OR during a flash-crash / liquidity-pull where top-20 depth briefly thins.
**Module**: [`praxis/core/execution_manager.py`](../praxis/core/execution_manager.py) — `_process_command` calls [`estimate_slippage`](../praxis/core/estimate_slippage.py) at line 949 but only logs the result; no rejection path. The estimator computes `simulated_vwap` and `slippage_estimate_bps` (VWAP vs mid) and returns; the command proceeds to `venue_adapter.submit_order` regardless.

The slippage estimator is wired into the pre-submit path for observability — every MARKET order log line carries `slippage_estimate_bps=...` — but there is no threshold-and-reject layer on top of it. A MARKET BUY against a pathologically thin book (flash-crash moment, exchange outage half-recovered, liquidity-provider pulled) would execute at whatever effective price the book offers, with `slippage_estimate_bps` merely logged. The capital ledger remains correct under the post-v0.73.0 `quoteOrderQty` reservation (the spend is exactly the reserved USDT, no ledger divergence is possible) but the strategy/operator receives whatever BTC qty that USDT bought; under thin-book conditions the actual BTC received could be materially below the strategy's expected sizing.

**When to fix**: When either (a) an incident traces back to a thin-book bad fill where the strategy's expected BTC sizing diverged materially from the actual BTC received, OR (b) order sizing scales up significantly (e.g. ≥ $1k per order).

**Migration**: Pre-submit guard in [`ExecutionManager._process_command`](../praxis/core/execution_manager.py) between the existing `estimate_slippage` call (line 949) and `submit_order`. Policy shape: `max_market_slippage_bps: int` config (default ~50, per-symbol override on [`TradingConfig`](../praxis/trading_config.py)). On violation, build a synthetic REJECTED `TradeOutcome` with `reason='EXECUTION_GUARD_SLIPPAGE_EXCEEDED'` and structured extras (`estimate.slippage_estimate_bps`, `policy.max_market_slippage_bps`, `book.top_of_book`, `cmd.symbol`) and short-circuit the venue submission. No auto-convert to LIMIT in v1 — that's a separate execution-mode feature with its own design surface. Only applies to MARKET orders; LIMIT orders self-cap via the price field.

## TD-079: Quote-native terminal signal only on REST submit-response path — WS-driven fills do not flip to FILLED

**Origin**: Pre-PR audit of v0.73.0 quote-native MARKET BUY
**Severity**: Low under current scope. Quote-native uses only Binance MARKET BUY today, and Binance returns immediate fills + `status=FILLED` synchronously in the REST submit response. So the WS path is never the terminal signal for the order shapes we actually ship. Elevated when (a) a LIMIT or post-only quote-native path is added, or (b) the REST response is lost mid-flight and the rescue path returns `status=FILLED` with no fills (round-1 fix already gates the terminal flip on `filled_qty > _ZERO`, so this case correctly defers to WS today — but WS doesn't pick it up).
**Module**: [`praxis/core/execution_manager.py`](../praxis/core/execution_manager.py) — only the immediate-fill submit-response path appends [`OrderQuoteNativeFilled`](../praxis/core/domain/events.py) (line 1080). The WS-driven [`_emit_ws_outcome`](../praxis/core/execution_manager.py) has no arm that appends `OrderQuoteNativeFilled`, and [`praxis/trading.py`](../praxis/trading.py) reconciliation does not look at venue `FILLED` status for quote-native orders.

A quote-native order that lands via WS fills only (REST-lost rescue scenario, or any future LIMIT quote-native path) would project to `Order.status = PARTIALLY_FILLED` in `TradingState._update_order_on_fill` and stay there indefinitely — `Order.qty is None` so the `filled_qty >= qty` self-termination path is skipped by construction. Spine replay would reconstruct the same stranded state. The trade outcome itself still emits correctly (the WS outcome path reads `order.status == FILLED` from the venue event, not from the projection), so capital release works; the gap is the projection — the order stays in `runtime.orders[client_order_id]` forever, which inflates the open-orders pull and confuses any boot-time reconciler that walks `runtime.orders`.

**When to fix**: Before a LIMIT or post-only quote-native order shape ships. Also fix if an incident traces a stranded `PARTIALLY_FILLED` order to a REST-lost rescue scenario.

**Migration**: Add an `OrderQuoteNativeFilled` emission to [`_emit_ws_outcome`](../praxis/core/execution_manager.py) for the `FillReceived` arm when the underlying venue event reports terminal status AND the cached `cmd.is_quote_native`. Symmetric: extend the boot reconciler in [`praxis/trading.py`](../praxis/trading.py) to recognize venue-reported `FILLED` on quote-native and synthesize `OrderQuoteNativeFilled` against the spine before replay reconstructs state. Both changes are local additions, not behavior changes for the currently-shipped MARKET BUY shape.

## TD-080: `_ensure_entry_position` quote-native placeholder relies on `_grow_position`'s VWAP zeroing

**Origin**: Greybeard pre-PR review during v0.73.0 pr-prep
**Severity**: Low under current scope (BTCUSDT-only, the placeholder is overwritten on the first fill, which happens within the same tick for MARKET orders). Elevated if `_grow_position` is ever refactored to add price stickiness, or if quote-native shapes ever produce a Position that persists across multiple ticks before first fill.
**Module**: [`praxis/launcher.py`](../praxis/launcher.py) — `_ensure_entry_position` falls back to `Decimal('1')` as `entry_price` when `action.quote_qty is not None` and no reference_price is available.

The fallback is correct *only* because [`OutcomeProcessor._grow_position`](https://github.com/Vaquum/Nexus/blob/main/nexus/infrastructure/praxis_connector/outcome_processor.py) computes `new_entry_price = (old_size * position.entry_price + fill_size * fill_price) / new_size`, and `old_size == 0` zeroes the `old_size * position.entry_price` term — so the arbitrary `Decimal('1')` is discarded on the first fill. The sentinel is load-bearing on that math: if a future Nexus refactor adds a price-sticky term (e.g. `max(position.entry_price, ...)` or a weighted-average that doesn't zero at `old_size == 0`), the `Decimal('1')` sentinel suddenly becomes a real entry price reported back to operators / risk / PnL — silently $1 / BTC instead of the actual fill price.

**When to fix**: Before any Nexus `_grow_position` refactor that changes the `old_size == 0` semantics, OR if an incident traces a wrong `entry_price` on a freshly-opened quote-native position. The pre-fix-trigger watch is a Nexus PR that touches `_grow_position`.

**Migration**: One of three:
1. Defer the placeholder Position creation until the first fill arrives (lazy create in `OutcomeProcessor`). This is a Nexus-side change.
2. Compute a real `entry_price` upfront from the order book (Praxis fetches `query_order_book(symbol)` and uses the best ask). Adds one venue call per quote-native ENTER.
3. Make the placeholder `entry_price` field `Decimal | None` end-to-end (Position.entry_price becomes optional when `size == _ZERO`), and have downstream readers handle `None`. Wider blast radius.

Option 1 is cleanest if Nexus accepts the lazy-create change; option 2 is the safest local fix if not.

## TD-081: binsim `Account.fills` (in-memory) and `Account.seen_client_order_ids` (in-memory + persisted + on-loop-sorted) grow unboundedly

**Origin**: Pre-PR review of `fix/binsim-ledger-snapshot-blocking-io` (v0.75.0 — issue #135 snapshot-cost fix)
**Severity**: Low under current scope, but with a residual disk + on-loop-sort component that v0.75.0 did NOT close. The v0.75.0 fix dropped `fills` from snapshot persistence and moved the disk write off the loop — closes the cited `-1003` cascade for the fills term. `Account.fills` from this point on is in-memory only (RSS growth, no disk, no loop blocking). `Account.seen_client_order_ids` is different: it is still persisted via `_account_to_dict` (`sorted(account.seen_client_order_ids)` runs on the event loop above the `to_thread` boundary, every snapshot), so the on-disk payload and the on-loop sort both grow linearly with cumulative order count. The `apply_order` hot path adds one entry per order. At the observed prod fill rate (~700 fills/hr per account) `fills` accrues ~17 MB per account per day in RSS; `seen_client_order_ids` accrues ~50 B per coid in both RSS and on disk, plus an O(n log n) sort on every snapshot at the same rate. The disk and on-loop-sort components are a partial residual of #135 rather than a new RSS-only concern. Elevated when the per-process RSS hits a deploy-relevant threshold OR when the snapshot payload grows past the depth-poll staleness budget.
**Module**: [`praxis/binsim/ledger.py`](../praxis/binsim/ledger.py) — `apply_fill` (`account.fills.append(fill)`), `apply_order` (`account.fills.extend(records)` + `account.seen_client_order_ids.add(client_order_id)`), `_account_to_dict` (`sorted(account.seen_client_order_ids)` runs on the event loop).

`fills` is only used by `Ledger.fills(account_id)` which has no production reader; `binsim.server._my_trades_stub` returns `[]` and there is no other consumer beyond tests. The list could be evicted entirely without changing observable behaviour, or replaced with a counter (`fills_count`) if tests want to assert the append happened. `seen_client_order_ids` is load-bearing for dedup but only the recent horizon matters in practice — real Binance's server-side dedup window is finite; a rolling LRU bounded at `N` most recent ids matches that semantics while bounding both the set itself and the per-snapshot sort cost.

**When to fix**: When either (a) binsim OOMs in a long-running deploy, OR (b) the snapshot payload grows back into the staleness-budget pathology (the `seen_client_order_ids` component still has the linear-growth shape that #135 measured for the `fills` component), OR (c) any new in-process consumer of `Ledger.fills(account_id)` lands and the cost of holding fills becomes load-bearing. The v0.75.0 snapshot fix is sufficient for the `fills` component of the disk/event-loop concern that #135 raised; this entry tracks both the adjacent in-memory concern and the residual disk + on-loop-sort concern so the next bound pass closes the full surface.

**Migration**: Two options.
1. **Drop `fills` entirely and bound `seen_client_order_ids`**. `fills` has no production reader: replace `Account.fills: list[LedgerFill]` with `Account.fills_count: int`, update `Ledger.fills(account_id)` to return `[]` or drop the API, update tests accordingly. Replace `seen_client_order_ids: set[str]` with a `collections.OrderedDict[str, None]` LRU-bounded at `N` (LRU-evict on insert past the limit) — `N` chosen to comfortably exceed the longest expected client retry window (Binance's documented server-side dedup is ~24h, so 100 k is generous). Also moves the `sorted(...)` call out of `_account_to_dict` (the LRU is already ordered).
2. **Bound both with rolling windows**. Keep `fills` as a `collections.deque(maxlen=N)` and treat `seen_client_order_ids` as above. Preserves the `Ledger.fills` API at the cost of a tunable memory ceiling and a bounded miss rate.

Option 1 is the minimum-change path if `Ledger.fills` is confirmed never-read in production. Option 2 preserves the API and trades a tunable memory ceiling for a bounded miss rate. Either option also closes the residual on-loop-sort cost in `_account_to_dict` once the underlying container is an ordered/bounded structure.

## TD-082: `Launcher.build_context` closure late-binds `outcome_processor` (RESOLVED in v0.76.0)

**Resolved** in v0.76.0 during PR review (Vaquum/Praxis#143, round 4). The launcher now pre-binds `outcome_processor: OutcomeProcessor | None = None` above the `build_context` closure definition; the later `outcome_processor = OutcomeProcessor(...)` reassigns the same name and the closure resolves it at call time. The `UnboundLocalError` hazard no longer exists on any startup-order refactor. Entry retained as historical record.

---

## TD-095: `OutcomeTranslator` re-derives `actual_fees` from a constant rate, not the venue fill fee

**Origin**: Fee-accounting fix (post-Conduit), Greybeard pre-PR review
**Severity**: Low (exact for binsim's flat 10 bps; diverges only on a variable-fee venue)
**Module**: `praxis/outcome_translator.py`

`_build_partial` / `_build_filled` compute `actual_fees = delta_notional * self._fee_rate` from a single `fee_rate` (now `_DEFAULT_FEE_RATE` = 0.001). The venue's own per-fill fee is present on `FillReceived.fee` but is not threaded into the Praxis `TradeOutcome` aggregate the translator consumes, so it cannot be passed through. For binsim's flat 10 bps taker fee the constant is exact; on a venue with a maker/taker split, tiered fees, or a BNB discount, the re-derived `actual_fees` diverges from the true fill fee and mis-states realized PnL by the difference.

**When to fix**: Before mainnet, OR when maker orders / fee tiers are in use.
**Migration**: Thread the venue-reported `fee` (and `fee_asset`) from `FillReceived` through `Order` and the Praxis `TradeOutcome` aggregate into the translator, and emit it verbatim as `actual_fees` instead of re-deriving from `fee_rate`.

---

## TD-096: `TradeClosed` close-detection is side-based, not full-close-aware — RESOLVED

---

## TD-097: Boot outcome-replay runs after the venue user stream opens, not before

**Origin**: TD-052 boot-replay deferral (codex review)
**Severity**: Low (Nexus#86 durable dedup makes the overlap a no-op, not a double-apply)
**Module**: `praxis/launcher.py` (`_replay_unacked_outcomes` in `_build_nexus_runtime`); `praxis/trading.py` (`Trading.start` / `_startup_account`)

`launch()` calls `_start_trading()` (which opens the Binance user stream in `_startup_account`) before `_start_nexus_instances()`, so the TD-052 boot replay hooks before the Nexus loops but AFTER the venue stream is live. A live WS outcome and a replayed outcome can therefore race for the same command during boot. This is acceptable today only because the replayed and live legs carry the same deterministic `outcome_id` and Nexus's durable `processed_outcome_ids` dedup drops the duplicate.

**When to fix**: If the boot-window race ever needs to be eliminated structurally (e.g. before relying on replay without the Nexus dedup, or on a venue without idempotent application).
**Migration**: Split `Trading.start()` into a recovery phase (state replay + reconcile) and a venue-stream phase, run the outcome replay between them, and open the user stream only after replay completes.

---

## TD-098: Delivery-context recording on the consumer-registration path is best-effort

**Origin**: TD-052 boot-replay deferral (codex review)
**Severity**: Low (the authoritative pre-registration path records the context durably; this path is the unknown-submission fallback)
**Module**: `praxis/launcher.py` (consumer-side `command_contexts` registration in `_build_nexus_runtime`)

The pre-registration path (`pre_register`) appends `OutcomeDeliveryContextRecorded` durably before the `send_command` handoff, so a normal submission's context survives a restart. The legacy consumer-registration path — which rebuilds an `OrderContext` when an outcome arrives for a command with no pre-registered context — does NOT append the context, because by then the command has already been submitted and a durable record before the fact is impossible. An outcome whose context was only ever built on this path is not replayable after a restart (boot replay skips it with a no-context warning).

**When to fix**: If unknown-submission recovery ever becomes a normal (non-exceptional) path, or before relying on replay for commands that bypass pre-registration.
**Migration**: Append a best-effort `OutcomeDeliveryContextRecorded` when the consumer rebuilds the context, accepting that it lands after submission rather than before; or eliminate the consumer-registration path in favour of always pre-registering.

## TD-099: Boot replay cannot re-apply a never-applied entry fill whose capital order was cleared

**Origin**: TD-052 boot-replay edge (pre-PR review)
**Severity**: Low (guarded against a re-fail loop; the divergence is owned by the boot capital reconcile)
**Module**: `praxis/launcher.py` (`_process_nexus_outcome` via `_replay_unacked_outcomes`); cross-repo: `nexus/core/capital_controller/capital_controller.py` (`reconcile_at_boot`, `order_fill`)

A boot-replayed ENTRY fill calls `CapitalController.order_fill(command_id)`, but `reconcile_at_boot` rebuilds `_orders` empty before replay runs, so `order_fill` returns `order not found` and the leg cannot be applied. The common replay case (outcome applied and persisted, only the `OutcomeAcked` lost) is unaffected — Nexus#86's durable dedup no-ops it. The never-applied case is a venue↔Nexus capital divergence: the venue filled, but Nexus discarded the in-flight order at boot.

The re-fail loop is guarded: a failed replay leg records `OutcomeReplayAbandoned`, which `_plan_outcome_replay` subtracts so the leg is not retried on later boots. The underlying divergence is NOT reconciled by replay.

**When to fix**: Before relying on replay to recover venue-filled-but-Nexus-unaware entries (e.g. mainnet, or if `reconcile_at_boot` stops releasing stranded in-flight capital).
**Migration**: Have the boot capital reconcile (`_reconcile_capital`) detect and settle a venue position with no matching Nexus capital order (reconstruct the fill from the spine `FillReceived`), rather than expecting outcome replay to re-apply it through `order_fill`.

## TD-100: Replay API enforces the bar cap only after loading the full range

**Origin**: replay-engine branch (pre-PR review)
**Severity**: Low (the API is loopback-only, so the caller is trusted/local)
**Module**: `praxis/replay/replay_api.py` (`post_replay`); `praxis/replay/load_replay_bars.py`

`POST /replay` calls `load_replay_bars` to read and join the full requested `[start, end]` window into `ReplayBar`s, and only then rejects the request if the bar count exceeds `max_bars`. A loopback caller can still force the full read/join (memory + CPU) for an oversized range before receiving the `400`.

**When to fix**: If the endpoint ever serves a less-trusted caller, or replay ranges grow large enough that the pre-rejection load is itself costly.
**Migration**: Push the cap into `load_replay_bars` (count or slice the prediction frame's `ts` against `[start, end]` and the limit before materializing all `ReplayBar`s), so an over-limit range is rejected before the full join.

## TD-101: run_replay couples to Launcher private members

**Origin**: replay-engine branch (pre-PR review)
**Severity**: Low (internal package; the `run_replay` end-to-end test catches a break, and replay is dev-only)
**Module**: `praxis/replay/run_replay.py`; `praxis/launcher.py`

`run_replay` drives the live pipeline by calling `Launcher` private members directly — `_start_event_loop`, `_start_trading`, `_build_nexus_runtime`, `_outcome_queues`, `_trading`, `_loop`, `_event_spine`, `_stop_event`, `_shutdown`. There is no public seam or boundary test asserting those exist, so a `Launcher` assembly refactor can silently break replay (caught only by the `run_replay` e2e test, not at the call site).

The related `strategy_source` execution risk is accepted and bounded: `replay_api` is loopback-only (a middleware rejects non-local peers) and the behaviour is documented in the module docstring; TD-100 bounds the request's range cap.

**When to fix**: when the `Launcher` per-account assembly is next refactored, or before replay is run outside a trusted dev host.
**Migration**: expose a public `Launcher` seam for replay (a build-runtime-without-loops entrypoint plus accessors for the spine / loop / per-account outcome queue) and have `run_replay` use it instead of reaching into privates.

## TD-102: Replay does not run the Nexus ShutdownSequencer

**Origin**: replay-engine branch (pre-PR review)
**Severity**: Low (deliberate; does not affect a replay's fills or realized PnL over the bar range)
**Module**: `praxis/replay/run_replay.py`

`run_replay` builds a `_NexusRuntime` and tears the run down via `launcher._shutdown()` (which only joins live Nexus threads — none are started in replay); it does not run `ShutdownSequencer`. So strategy `on_shutdown` / `on_save`, the final Nexus checkpoint, and instance deregistration do not fire. This is deliberate: shutdown is an operational event, not part of the replayed market timeline, and a throwaway replay instance has no state to persist or deregister — running `on_shutdown` could fire close-on-shutdown actions that do not belong in the replayed history. Recorded for traceability.

**When to fix**: if replay must reproduce the live end-of-run lifecycle (e.g. measuring an `on_shutdown` close-all), or if replay strategies need `on_save` state carried across runs.
**Migration**: run a `ShutdownSequencer` pass at the end of `run_replay` against the isolated runtime, accepting that its actions land on the spine after the last bar.

## TD-103: Replay API run registry grows unbounded

**Origin**: replay-engine branch (pre-PR review)
**Severity**: Low (in-memory; only matters if the replay API runs as a long-lived service)
**Module**: `praxis/replay/replay_api.py`

`build_replay_app` keeps every run's `_RunRecord` in an in-memory dict keyed by `run_id`, never evicted. A short-lived / dev invocation is fine, but a long-lived API process accumulates one record per run forever (each holding a `ReplayResult`), so memory grows without bound.

**When to fix**: before running the replay API as a persistent service rather than per-session.
**Migration**: add a bounded registry (LRU or TTL eviction, or persist results and drop in-memory records after a window) and have `GET /replay/{run_id}` return 404/410 for an evicted id.

## TD-104: Parallel replays need per-run strategy-module isolation

**Origin**: replay-engine branch (pre-PR review)
**Severity**: Low (the API executor is single-worker, so runs serialize and cannot collide today)
**Module**: `praxis/replay/replay_api.py`; `praxis/replay/run_replay.py`

`run_replay` writes the scenario's strategy to `work_dir` and the launcher imports it; the API executor is `max_workers=1`, so runs serialize and never import concurrently, and `sys.path` is cleaned per run (the launcher loads via `spec_from_file_location`, so there is no `sys.modules` collision today). Before raising the worker count to run replays in parallel, per-run module isolation must be in place so concurrent imports of same-named strategy modules cannot interfere.

**When to fix**: before bumping the executor worker count above 1.
**Migration**: give each run a unique strategy module name (or an isolated import context), verify no shared import state leaks across concurrent runs, then raise `max_workers`.

## TD-105: Replay drops strategy on_startup actions

**Origin**: replay-engine branch (PR #159 review)
**Severity**: Low (the Conduit strategies enter on signal, not startup; out of scope for phase one)
**Module**: `praxis/replay/run_replay.py`; `praxis/launcher.py` (`_build_nexus_runtime`)

A strategy's `on_startup` actions are drained inside `_build_nexus_runtime` (via `sequencer.drain_pending_startup_actions`), which runs before `run_replay` forces ACTIVE mode (`_activate_mode`), sets the bar price (`adapter.set_price`), or materialises any frame. So a startup action is submitted while the instance is `REDUCE_ONLY` and the price context is unset, and is rejected (`OrderRejectedError('no_price')` / mode gate) and recorded as a silently-dropped `OrderSubmitFailed`. A strategy that opens its initial position on startup rather than on the first signal would diverge from a live/paper run with no warning. `_activate_mode` cannot run before the build because it needs the `runtime.state` the build creates.

**When to fix**: before supporting strategies that enter on `on_startup` in replay.
**Migration**: refactor the launcher so a replay can force ACTIVE mode + seed the opening price + materialise the first bar before the in-build startup drain (or expose a build hook that runs the drain after that context is set). Relates to the public-replay-seam work in TD-101.

## TD-106: /metrics reads the whole epoch spine per request

**Origin**: Limen-parity metrics branch (Greybeard pre-PR review)
**Severity**: Low (on-demand loopback endpoint, not a hot path)
**Module**: `praxis/launcher.py` (`_metrics_handler`)

`_metrics_handler` calls `EventSpine.read(epoch_id)` and filters the full result in Python on every request. A multi-day paper epoch accumulates one `MarkSampled` per sample interval plus every fill, so each `/metrics` hit reads and rebuilds the entire epoch's events. Same class as TD-103's unbounded replay registry.

**When to fix**: before the endpoint is polled frequently or a paper epoch runs long enough for the read to dominate response time.
**Migration**: read only the account's events (a spine query filtered by `account_id`), and/or cache the built report between samples and invalidate on new fills.

## TD-107: Account-ledger projection failures are swallowed

**Origin**: Account sub-system branch (Greybeard pre-PR review)
**Severity**: Low (the ledger is a secondary projection; the Event Spine remains the durable record)
**Module**: `praxis/core/execution_manager.py` (`_project_to_ledger`)

`_project_to_ledger` wraps `AccountLedger.apply` in a broad `except` that logs and never propagates, so a booking failure cannot break the trading path. The trade-off is that the "authoritative books" can silently and permanently stop booking — e.g. if a fill reaches an unregistered ledger, every subsequent fill for that account is swallowed and only a log line records it. Nothing surfaces the drift to an operator.

**When to fix**: before the ledger balances back any user-facing reporting or reconciliation that must be trusted without cross-checking the spine.
**Migration**: add a metric/alert on ledger projection failures (count per account), or a periodic reconciliation of the ledger against a spine replay, so silent drift is detected rather than only logged.

## TD-108: FundTransaction has no spine-level idempotency

**Origin**: Account sub-system branch (Greybeard / Copilot pre-PR review)
**Severity**: Low (replay applies each spine event once; the risk is a duplicate append, not replay)
**Module**: `praxis/infrastructure/event_spine.py`; `praxis/core/account_ledger.py` (`_on_fund_transaction`)

`FundTransaction` carries a stable `fund_transaction_id`, but the spine only deduplicates `FillReceived` (on `venue_trade_id`). A duplicate `FundTransaction` append would double-book capital against `Equity:Contributions` with nothing to stop it; the id is stored for a future dedup that does not exist yet.

**When to fix**: before a fund-transaction producer that can retry appends (e.g. a deposit API or Nexus-driven top-up) is wired in.
**Migration**: extend the spine dedup to key `FundTransaction` on `fund_transaction_id` (as `FillReceived` does on `venue_trade_id`), so a duplicate append is a no-op.
