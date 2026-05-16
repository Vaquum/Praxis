# Technical Debt

Known technical debt in shipped code. Each item includes origin PR, severity, and migration path.

---

## TD-009: VWAP re-read from spine on abort

**Origin**: PR #52 (PR review)
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

**Origin**: PR #72 (PR review)
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

---

## TD-029: `command_contexts` and `command_strategy_ids` leak when `_grow_position` / `_reduce_position` raises

**Origin**: Round-14 8-pass aggregation
**Severity**: Low (bounded; few raise sites)
**Module**: `praxis/launcher.py` (`process_outcome` terminal-cleanup block after `outcome_processor.process(...)`); cross-repo `nexus/infrastructure/praxis_connector/outcome_processor.py:325-381` (raise sites)

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

**Origin**: Round-18 codex-supervised audit (Pass 8)
**Severity**: Low (defense-in-depth; normal path appends `OrderSubmitIntent` before REST POST)
**Module**: `praxis/trading.py:451-494` (`_reconcile_account`); `praxis/core/execution_manager.py:329-380` (`reconcile_orphan_commands`)

Boot reconciliation walks `trading_state.orders` (rebuilt from EventSpine) and queries the venue for each known order. It does NOT enumerate the venue's full open-order list (`query_open_orders`). `reconcile_orphan_commands` only flags `CommandAccepted`-without-followup. Combined, no path discovers an open venue order whose `OrderSubmitIntent` / `OrderSubmitted` was never appended to spine (e.g., SIGKILL between venue ACK and `event_spine.append`).

**When to fix**: Before any deployment with manual order placement on the same account, OR if mid-run spine writes ever fail after venue ACK in observed traffic.
**Migration**: At end of `_startup_account`, call `query_open_orders(account_id)` and synthesize `OrderSubmitIntent` + `OrderSubmitted` events for any venue order with no local projection. Or escalate to operator log instead of auto-correcting.

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

## TD-045: Symbol filters not loaded for fresh accounts; `_validate_order` fails open

**Origin**: Round-18 codex-supervised audit (Pass 10)
**Severity**: Low (Binance applies its own filter checks; rate limit waste only)
**Module**: `praxis/trading.py:302-304` (`_startup_account`); `praxis/core/execution_manager.py:219-243` (`active_symbols`); `praxis/infrastructure/binance_adapter.py:958-962` (`_validate_order` cache miss)

`load_filters` runs only when `active_symbols(account_id)` is non-empty at boot, which requires existing orders or positions from the spine. A fresh account with no exposure starts with no filters loaded for the strategies' target symbols. `BinanceAdapter._validate_order` logs a warning and returns without validation when cache misses (`self._filters.get(symbol) is None`). Binance's server-side check is the only remaining safety net.

**When to fix**: Before any deployment where venue rate-limit budget matters, OR alongside MAJOR-007 (filter ValueError orphan) — the no-preload fail-open path is what currently shields fresh accounts from MAJOR-007's orphan trap.
**Migration**: At boot, walk the manifest's strategy specs to compute the union of intended symbols and call `load_filters(symbols)` before any strategy callback fires. Alternatively, on-demand load inside `_validate_order` on cache miss.

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

## TD-052: Boot replay-from-spine for unconsumed `TradeOutcomeProduced` events

**Origin**: Round-18 MAJOR-004 part B scope deferral (Praxis #86)
**Severity**: Major (closes the cross-restart half of MAJOR-004; runtime retry already lands)
**Module**: `praxis/trading.py` (`Trading.start`); `praxis/outcome_translator.py` (`_new_outcome_id`); cross-cutting (`OutcomeAcked` event already exists)

MAJOR-004 part B added a runtime retry for `_on_trade_outcome` callback failures and a durable `OutcomeAcked` marker that the launcher's `process_outcome` appends after `OutcomeProcessor.process` returns success. Boot replay-from-spine — re-delivering `TradeOutcomeProduced` events that lack a matching `OutcomeAcked` — was scoped out because it requires translator-determinism prework: `outcome_translator._new_outcome_id` currently generates `uuid.uuid4().hex` per call, so re-translating the same Praxis `TradeOutcome` after restart produces NEW Nexus `outcome_id`s that do NOT match Nexus's idempotency dedup set. Without stable IDs, boot replay would either skip outcomes (if matched on a non-existent Praxis-side outcome_id) or double-apply them (if Nexus dedup misses).

The runtime retry handles transient callback failures; the `OutcomeAcked` event is already on the spine for forward use. Cross-restart loss of an outcome that was produced but never consumed by Nexus still requires manual operator intervention (e.g., re-issue the command).

**When to fix**: Before any sustained multi-day paper trading where dropped outcomes accumulate, OR before MAJOR-005 / future audits surface this as a hot path.

**Migration**:
1. Add stable `outcome_id: str` field to `praxis.core.domain.trade_outcome.TradeOutcome` (in-memory) and to the `TradeOutcomeProduced` event (durable) — generated once in `ExecutionManager._build_outcome` / `_emit_ws_outcome`.
2. Update `OutcomeTranslator` so derived Nexus outcome_ids are deterministic from the Praxis `outcome_id` (e.g., `f"{praxis_outcome_id}-{seq}"`).
3. In `Trading.start`, after `replay_events` and `reconcile_orphan_commands`, scan per-account `TradeOutcomeProduced` events. For each, compute the full set of derived Nexus `outcome_id`s (per step 2) and consider the produced event consumed only when ALL derived ids appear as `OutcomeAcked.outcome_id` (and, once TD-086 ships, also covered by the Nexus-side durable applied-outcome marker). Re-deliver any `TradeOutcomeProduced` with at least one un-acked derived id by reconstructing the Praxis `TradeOutcome` from the spine fields and dispatching via `self._on_trade_outcome`; Nexus-side dedup catches the derived outcomes that were already applied.
4. Nexus's in-memory dedup (already keyed on outcome_id from MAJOR-004 part A) catches re-delivered outcomes within a single process lifetime. Cross-restart safety requires BOTH the derived-id-set `OutcomeAcked` filter at boot-replay-emission time AND the Nexus-side durable applied-outcome marker from TD-086 — the `OutcomeAcked` filter alone is insufficient because Nexus may have applied the outcome and persisted a checkpoint before the ack landed (see acceptance addendum).
5. Add integration test: simulate Nexus crash after spine append but before consumption → restart → boot replay drives Nexus to the same end state as if no crash had occurred.

**Acceptance addendum (codex-supervised audit re-run, 2026-05-04)**:
- Replay must handle the case where Nexus state was checkpointed (via `_final_checkpoint` at shutdown OR via `_reconcile_capital` boot adjustment) AFTER memory mutation but BEFORE `OutcomeAcked` was emitted.
- Replay must NOT assume "missing `OutcomeAcked`" implies "Nexus did not mutate". The check must consult a durable Nexus-side applied-outcome record OR the replay consumer must produce the same end-state as a successful first delivery did (idempotent `_handle_*`).
- Boot replay scan order: read all `TradeOutcomeProduced` for epoch. The fan-out granularity matters — a single Praxis `TradeOutcome` can produce multiple Nexus `NexusTradeOutcome`s (ACK + zero-or-more PARTIALs + a terminal), each with its own Nexus `outcome_id`, and `OutcomeAcked.outcome_id` records the Nexus id, not the Praxis id. The migration's step 2 (deterministic derived Nexus outcome_ids from the stable Praxis `outcome_id`, e.g. `f"{praxis_outcome_id}-{seq}"`) is what lets the boot-replay filter work: for each `TradeOutcomeProduced`, compute the full set of derived Nexus outcome_ids and re-deliver iff ANY derived id lacks a matching `OutcomeAcked` (and is not already covered by a Nexus-side durable applied-outcome marker). Re-delivery goes through the same callback chain; Nexus-side dedup catches the derived outcomes that were already applied.
- TD-052 must NOT ship without TD-086 (paired implementation boundary).

---

## TD-053: HealthLoop demote to REDUCE_ONLY on sustained market-data failure

**Origin**: Round-18 MAJOR-005 part scope deferral (Praxis #86)
**Severity**: Major (defense-in-depth on top of validator PRICE-stage rejection)
**Module**: `praxis/market_data_poller.py`; cross-repo: `nexus/core/health_loop.py`, `praxis/core/domain/health_snapshot.py`

MAJOR-005 landed cache-freshness enforcement (`StaleMarketDataError` from `MarketDataPoller.get_market_data` after `max_age_seconds`, default `2 * kline_size`) and `fallback_price_provider` now returns `None` on stale data, so the validator's PRICE stage rejects ENTERs cleanly. The bigger M05.4 / M05.7 acceptance — counting consecutive `_fetch` failures and surfacing them to `HealthSnapshot` so HealthLoop demotes `state.mode` to `REDUCE_ONLY` (EXITs still work, ENTERs blocked) — was scoped out because it requires plumbing a new health-signal field into `HealthSnapshot`, wiring it through the `health_snapshot_provider` callback the launcher gives to `HealthLoop`, and verifying mode-transition semantics in the cross-repo loop.

The current behavior is safe for paper trading: stale data raises in the predict tick (loop catches, signal skipped), and stale fallback rejects ENTER at PRICE-stage. Mode demotion would add a single coherent system-wide signal instead of relying on per-callsite rejection.

**When to fix**: Before sustained mainnet operation, OR when a single operator-facing health signal is needed for "venue feed degraded; trading reduced".

**Migration**:
1. Add a `consecutive_fetch_failures: int` counter to `MarketDataPoller` (per-kline_size dict); reset on `_fetch` success, increment on failure.
2. Expose `health_status() -> dict[int, MarketDataHealth]` (or similar) reporting per-kline failure counts and stale flags.
3. Add a `market_data_healthy: bool` field to `HealthSnapshot` (Praxis-side dataclass); the launcher's `_build_health_snapshot` callback samples `MarketDataPoller.health_status()` and sets it.
4. In Nexus `HealthLoop` / `HealthEvaluator`, add a transition: `market_data_healthy=False` → `REDUCE_ONLY` (EXITs still work, ENTERs blocked).
5. Test: simulate repeated `_fetch` failures → after N attempts, snapshot reports unhealthy → HealthLoop demotes mode within next tick → validator's MODE stage rejects ENTERs.

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

## TD-060: `MarketDataPoller` test cleanup not protected by `try/finally`

**Origin**: Copilot review on PR #103 (fix/poller-fixed-cadence)
**Severity**: Low (test hygiene; theoretical pollution risk, never observed)
**Module**: `tests/test_market_data_poller.py` — 18 of 20 `poller.start()` callsites

Most `MarketDataPoller` tests follow the pattern `poller.start(); ...assertions...; poller.stop()` without a `try/finally` guard between them. If any assertion in the middle raises, `poller.stop()` is skipped and the daemon poller thread leaks for the rest of the pytest session. Once the calling test's `with patch('...get_spot_klines', ...)` context exits, the leaked thread reverts to the real `get_spot_klines` import and starts hitting Binance for real. The next test that patches the same symbol then sees its mock's `call_count` bumped by the leaked thread, causing flake.

The risk is real but theoretical: 18 unprotected sites have run consistently green across many CI cycles. Copilot flagged 3 specific instances on PR #103 but the lack of `try/finally` is the project-wide convention in this file, not a regression introduced by that PR.

**When to fix**: When a `poller.*` test starts flaking in CI for unexplained reasons (the leaked-thread pollution mechanism would be a candidate), OR when the next refactor of `tests/test_market_data_poller.py` happens for any other reason and the sweep cost is amortised.

**Migration**: Wrap all 18 `poller.start()`-with-assertion sites in `try/finally`:

```python
poller.start()
try:
    ...assertions...
finally:
    poller.stop()
```

Or extract a small `_run_with_poller(poller, fn)` context manager / pytest fixture so individual tests don't pay the boilerplate. Keep the 2 already-wrapped sites (which use the right pattern) as the template.

---

## TD-061: Synchronous Limen + binancial fetches block `Launcher.launch()` for minutes

**Severity**: Medium (operator UX; no correctness impact)
**Module**: `praxis/launcher.py:_start_poller` (introduced by Vaquum/Praxis#108)

`_start_poller` calls `MainCache.bootstrap_if_empty()` (downloads ~100MB HF snapshot when the disk parquet is missing) and `MainCache.refresh_from_binancial()` (walks Binance trades for the trailing window) synchronously inline in `launch()`. On first-ever boot, that's a few minutes of blocking work between `_start_trading` and `_start_nexus_instances` with no progress signal — `/healthz` is not yet listening either, so an operator sees a hung process. The choice was deliberate (Vaquum/Praxis#108 deploy plan) to ensure sensors see fresh data on the first tick after `_start_nexus_instances`, not 1 minute later.

**When to fix**: When boot latency starts mattering for ops (e.g. faster crash-recovery cycles, or once we have a watchdog that times out the initial fill). At that point, move the synchronous `refresh_from_binancial()` out of `_start_poller` and let `CacheScheduler`'s binancial thread fire it asynchronously; sensors get fresh data on the first scheduler tick (~60s post-boot).

**Migration**: Drop `self._cache.refresh_from_binancial()` from `_start_poller`. Document the new "first 60s of uptime have ≤24h-stale data" contract in the launcher docstring.

---

## TD-062: `_aggregate_spot_klines` is a private Limen helper that Praxis depends on

**Severity**: Low (coupling, no correctness impact)
**Module**: `praxis/market_data_cache.py:30` (introduced by Vaquum/Praxis#108)

`MainCache.get_market_data` calls Limen's `_aggregate_spot_klines` (imported as `_limen_aggregate_spot_klines`) to aggregate 1-min bars up to the requested kline_size. No `# noqa: PLC2701` suppression on the import: PLC2701 isn't enabled in the current ruff config (the `PL` selector in `pyproject.toml` does not activate it for this codebase's ruff version), so adding the noqa would itself trip RUF100 (unused noqa). The aliased import name keeps the cross-package private dependency visible at the call site. That function is canonical (weighted mean, sum-of-squares for std, sum for volume / liquidity / maker_volume, first / last for OHLC) and reusing it avoids drift between training-time aggregation and live aggregation — but importing a private name across packages is fragile: a Limen rename or signature change would break Praxis without a deprecation warning.

**When to fix**: Either (a) ask the Limen team to expose `aggregate_spot_klines` as a public API (preferred — single source of truth), or (b) copy the function body + `_base_interval_seconds` + `_round_spot_kline_columns` helpers into Praxis (~120 LOC) and accept the drift risk.

**Migration**: For (a), once Limen ships a public name, swap the import to the public symbol. For (b), copy the three functions verbatim, add a comment pointing at the upstream version + Limen pin in `pyproject.toml` so a reviewer knows to re-sync on the next Limen pin bump. If a future ruff config enables PLC2701, add the `# noqa: PLC2701` suppression at the same time as either path.
