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

## TD-014: Single-writer concurrency violation in WS and reconciliation paths

**Origin**: Deep audit (MMVP closure review)
**Severity**: Critical (data races possible under concurrent fills + reconciliation)
**Modules**: `praxis/trading.py`, `praxis/core/execution_manager.py`

The RFC establishes a single-writer model where all `TradingState` mutations flow through the account coroutine. Two paths currently bypass this: the WebSocket fill handler and the reconciliation logic in `Trading.start()` both mutate `TradingState` directly. In single-account MMVP flows these paths do not race, but multi-account or concurrent fill+recon scenarios will produce state corruption.

**When to fix**: Before multi-account support or any path where fills and reconciliation can overlap.
**Migration**: Route WS fills and reconciliation results through the account coroutine's command queue so all state mutations are serialized through the single-writer.

