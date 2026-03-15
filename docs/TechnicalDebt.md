# Technical Debt

Known technical debt in shipped code. Each item includes origin PR, severity, and migration path.

---

## TD-001: EventSpine hydration assumes flat event dataclasses

**Origin**: PR #30 (review by @mikkokotila)
**Severity**: Low (all events are currently flat)
**Module**: `praxis/infrastructure/event_spine.py`

`dataclasses.asdict()` recursively converts nested dataclasses into plain dicts. `_hydrate` reconstructs only top-level fields via `get_type_hints`. If any event ever contains a nested dataclass, the round-trip will silently produce a dict where a dataclass is expected.

**When to fix**: Before adding nested dataclass fields to any event type.
**Migration**: Add nested-type detection in `_hydrate` that recursively reconstructs inner dataclasses from their dict representation.

---

## TD-002: Mutable domain models lack post-construction invariant guards

**Origin**: PR #24 (review comments)
**Severity**: Medium
**Modules**: `praxis/core/domain/order.py`, `praxis/core/domain/position.py`

`Order` and `Position` are mutable dataclasses. Validation runs in `__post_init__` only. After construction, direct attribute assignment can violate invariants (e.g. negative `qty`, `filled_qty > qty`). `TradingState` is the intended mutation controller, but nothing enforces that constraint.

**When to fix**: Before any code path mutates `Order`/`Position` outside of `TradingState`.
**Migration**: Add `__setattr__` guards, property setters with validation, or make fields private with validated mutator methods.

---

## TD-003: TradeCommand.execution_params not validated against execution_mode

**Origin**: PR #25 (review comments)
**Severity**: Low (only `SINGLE_SHOT` mode exists)
**Module**: `praxis/core/domain/trade_command.py`

`execution_params` is typed as `SingleShotParams` but `execution_mode` accepts any `ExecutionMode` enum value. A `TradeCommand` with `execution_mode=TWAP` and `SingleShotParams` is accepted without error.

**When to fix**: Before adding a second execution mode.
**Migration**: Widen `execution_params` to a union or protocol type and validate that the params type matches the selected mode in `__post_init__`.

---

## TD-004: FillReceived append atomicity relies on caller discipline

**Origin**: PR #31 (review comments)
**Severity**: Medium
**Module**: `praxis/infrastructure/event_spine.py`

`append()` for `FillReceived` performs two INSERTs: first into `fill_dedup`, then into `events`. If the second fails after the first succeeds, the dedup table is polluted and subsequent valid fills are silently dropped. The docstring states callers own transaction boundaries, but this is not enforced.

**When to fix**: Before production use with real fill data.
**Migration**: Enforce transaction context via `SAVEPOINT`, or validate that a transaction is active before executing the dual-insert path.

---

## TD-005: _hydrate calls get_type_hints per row on every read

**Origin**: PR #31 (review comments)
**Severity**: Low (epochs are small currently)
**Module**: `praxis/infrastructure/event_spine.py`

`_hydrate()` calls `get_type_hints(cls)` for every row returned by `read()`. This is repeated reflection work that scales linearly with epoch size. For large epochs the cost dominates `read()` time.

**When to fix**: Before epochs grow to thousands of events.
**Migration**: Precompute a `{event_type: hints}` map alongside `_EVENT_REGISTRY` at module load time and reuse it in `_hydrate`.

---

## TD-007: Duplicated retry loop in _signed_request and _api_key_request

**Origin**: §2.9 implementation
**Severity**: Low (two copies, no third expected)
**Module**: `praxis/infrastructure/binance_adapter.py`

`_signed_request` and `_api_key_request` share ~80 lines of identical retry/backoff/rate-limit logic. The only difference is URL construction (HMAC-signed query string vs plain params). This is manageable at two copies but would become a maintenance risk if a third request style is added.

**When to fix**: Before adding a third request method variant, or during post-WP-0003 cleanup.
**Migration**: Extract a `_request_with_retry(method, path, *, build_request, account_id)` that owns the retry loop, and have both methods delegate to it.

---

## TD-008: Linear order scan in _process_abort

**Origin**: PR #52 (Copilot review)
**Severity**: Low (typically 1-2 orders per account)
**Module**: `praxis/core/execution_manager.py`

`_process_abort` iterates `runtime.trading_state.orders` to find the order matching `abort.command_id`. This is O(n) in the number of open orders. For SingleShot mode with `sequence=0`, the `client_order_id` is deterministic and could be computed via `generate_client_order_id` for an O(1) dict lookup. However, this couples abort to the ID generation convention and the `sequence=0` assumption, which will not hold for multi-slice execution modes.

**When to fix**: When multi-slice modes (TWAP, ICEBERG) are implemented and order counts per account grow.
**Migration**: Add a `command_id → client_order_id` index in `_AccountRuntime` populated by `_process_command` on order submission, enabling O(1) lookup in `_process_abort`.

---

## TD-009: VWAP re-read from spine on abort

**Origin**: PR #52 (Copilot review)
**Severity**: Low (epochs are small currently)
**Module**: `praxis/core/execution_manager.py`

`_process_abort` computes VWAP by calling `EventSpine.read()` and filtering for `FillReceived` events matching the `client_order_id`. This re-reads and rehydrates the entire epoch for every abort with fills, scaling as O(events_in_epoch). The `Order` dataclass tracks `filled_qty` but not `avg_fill_price`.

**When to fix**: Before epochs grow to thousands of events or abort frequency increases.
**Migration**: Either add cumulative notional tracking to `Order`/`TradingState` so VWAP is available without spine re-read, or add a spine query method that fetches only `FillReceived` rows for a given `client_order_id`.

---

## TD-010: No venue LTP benchmark support for slippage analytics

**Origin**: §6.2 assessment follow-up
**Severity**: Low (RFC primary benchmark is mid-price)
**Module**: `praxis/core/execution_manager.py`, `praxis/infrastructure/venue_adapter.py`

RFC §6.2 defines walk-the-book slippage with mid-price as the primary benchmark and `reference_price` as supplementary. Praxis currently has no Venue Adapter API for last traded price (LTP), so slippage analytics cannot include a venue-LTP benchmark without caller-supplied price data.

**When to fix**: If Manager or analytics consumers require venue-native LTP-based slippage benchmarking.
**Migration**: Add a venue-agnostic LTP query method to `VenueAdapter` (with Binance implementation), compute and log optional LTP-based slippage metric alongside existing mid-price and reference-price metrics.

---

## TD-011: Trading accesses ExecutionManager private attributes

**Origin**: PR #59 (Copilot review)
**Severity**: Low (single consumer)
**Module**: `praxis/trading.py`

`Trading` accesses `ExecutionManager._accounts` and `_command_trade_ids` directly for reconciliation and WebSocket handling. This tight coupling makes future refactors risky.

**When to fix**: Before adding additional consumers of ExecutionManager internals.
**Migration**: Add small public accessors on ExecutionManager (e.g., `get_trading_state(account_id)`, `trade_id_for_command(command_id)`) and use those instead of reaching into private attributes.

---

## TD-012: Event filtering is O(accounts × events) during startup

**Origin**: PR #59 (Copilot review)
**Severity**: Low (epochs and accounts are small currently)
**Module**: `praxis/trading.py`

`Trading.start()` reads the full epoch and then scans it for each account with a list comprehension. This is O(events × accounts) and can become costly as epochs/accounts grow.

**When to fix**: Before epochs grow to thousands of events or account counts increase significantly.
**Migration**: Group events by `account_id` in a single pass (e.g., build a `dict[account_id, list[(seq, event)]]`) before the loop, or add an EventSpine query that reads only events for a given account.

---

## TD-013: replay_events lacks command context for abort processing

**Origin**: PR #59 (Copilot review)
**Severity**: Medium (aborts for replayed commands will be dropped)
**Module**: `praxis/core/execution_manager.py`

`replay_events()` populates `_accepted_commands`/`_terminal_commands` but does not rebuild `_commands` metadata. `_process_abort()` requires `self._commands[command_id]` to look up `order_type`/`symbol`, so aborts for replayed (pre-restart) commands will be accepted by `validate_trade_abort` but then ignored as "abort for unknown command".

**When to fix**: Before supporting abort operations that span restarts.
**Migration**: Either reconstruct the minimal command data needed for aborts during replay (from `OrderSubmitIntent`), or update the abort path to operate from `TradingState` orders without requiring `_commands`.
