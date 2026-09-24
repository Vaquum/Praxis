# File ledger

Every domain file in Praxis and Nexus, and whether the wiki accounts for it.

`uncovered` no path walks it · `partial` some behaviour covered · `covered` local review accounts for its domain behaviour through reviewed rows or recorded exclusions.

A file reaches `covered` only when no unresolved candidate is attached to it. Pending candidates block it.

## Praxis — 95 files

| File | State | Rows |
|---|---|---|
| `praxis/core/execution_manager.py` | partial | P1-01 to P1-10 |
| `praxis/core/trading_state.py` | partial | P1-01 |
| `praxis/core/validate_trade_abort.py` | partial | P1-04 |
| `praxis/core/domain/trade_outcome.py` | partial | P1-04 |
| `praxis/infrastructure/binance_adapter.py` | partial | P1-07, P1-10 |
| `praxis/core/estimate_slippage.py` | partial | P1-06 |
| the other 89 | uncovered | — |

`execution_manager.py` is 10,867 lines. Ten rows touching it makes it `partial` by a wide margin, not nearly covered.

## Nexus — 81 files

| File | State | Rows |
|---|---|---|
| all 81 | uncovered | — |

Files are listed individually as tracing reaches them. Every untouched file stays listed as `uncovered`. That visibility is the pressure.

---

Created 2026-09-16 09:39 UTC · Last modified 2026-09-24 08:02 UTC
