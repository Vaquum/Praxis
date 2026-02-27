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
