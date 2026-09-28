# File ledger

Every domain file in Praxis and Nexus, and whether the wiki accounts for it.

`uncovered` no path walks it · `partial` some behaviour covered · `covered` local review accounts for its domain behaviour through reviewed rows or recorded exclusions.

A file reaches `covered` only when no unresolved candidate is attached to it. Pending candidates block it.

## Praxis — 95 files

| File | State | Rows |
|---|---|---|
| `praxis/core/execution_manager.py` | partial | P1-01 to P1-10, P2-11 to P2-25 |
| `praxis/core/domain/fill.py` | full | P2-15 |
| `praxis/core/account_ledger.py` | partial | P2-16, P2-29 |
| `praxis/core/domain/events.py` | partial | P2-15 |
| `praxis/core/trading_state.py` | partial | P1-01 |
| `praxis/core/validate_trade_abort.py` | partial | P1-04 |
| `praxis/core/domain/trade_outcome.py` | full | P1-04, P2-18 |
| `praxis/infrastructure/binance_adapter.py` | partial | P1-07, P1-10, P2-11, P2-25 |
| `praxis/trading.py` | partial | P2-11, P2-12 |
| `praxis/trading_inbound.py` | partial | P2-12 |
| `praxis/infrastructure/replay_venue_adapter.py` | partial | P2-12 |
| `praxis/core/trade_command.py` | partial | P2-24 |
| `praxis/core/validate_trade_command.py` | partial | P2-14, P2-24, P2-27, P2-28 |
| `praxis/core/domain/enums.py` | partial | P2-14, P2-19 |
| `praxis/core/domain/execution_scheme.py` | full | P2-19 |
| `praxis/core/domain/ladder_dca_params.py` | full | P2-20 |
| `praxis/core/plan_even_slices.py` | full | P2-19, P2-20 |
| `praxis/core/plan_weighted_slices.py` | full | P2-19, P2-20 |
| `praxis/infrastructure/event_spine.py` | partial | P2-17, P2-32 |
| `praxis/infrastructure/book_cache.py` | full | P2-26 |
| `praxis/infrastructure/book_poller.py` | full | P2-26 |
| `praxis/core/estimate_slippage.py` | partial | P1-06 |
| the other 84 | uncovered | — |

`execution_manager.py` is 10,867 lines. Ten rows touching it makes it `partial` by a wide margin, not nearly covered.

## Nexus — 81 files

| File | State | Rows |
|---|---|---|
| all 81 | uncovered | — |

Files are listed individually as tracing reaches them. Every untouched file stays listed as `uncovered`. That visibility is the pressure.

---

Created 2026-09-16 09:39 UTC · Last modified 2026-09-27 21:36 UTC
