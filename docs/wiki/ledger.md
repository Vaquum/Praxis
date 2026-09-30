# File ledger

Every domain file in Praxis and Nexus, and whether the wiki accounts for it.

`uncovered` no path walks it · `partial` some behaviour covered · `covered` local review accounts for its domain behaviour through reviewed rows or recorded exclusions.

A file reaches `covered` only when no unresolved candidate is attached to it. Pending candidates block it.

## Praxis — 95 files

| File | State | Rows |
|---|---|---|
| `praxis/core/execution_manager.py` | partial | P1-01 to P1-10, P2-11 to P2-25 |
| `praxis/core/domain/fill.py` | full | P2-15 |
| `praxis/core/account_ledger.py` | partial | P2-16, P2-29, P3-11, P3-12 |
| `praxis/core/generate_client_order_id.py` | full | P3-14 |
| `praxis/core/validate_trade_modify.py` | partial | P3-13 |
| `praxis/infrastructure/binance_ws.py` | partial | P3-16 |
| `praxis/infrastructure/mytrades_backfill.py` | full | P3-17 |
| `praxis/core/health_tracker.py` | full | P3-15 |
| `praxis/infrastructure/token_bucket.py` | full | P3-18 |
| `praxis/core/domain/health_snapshot.py` | full | P3-15 |
| `praxis/core/domain/modify_params.py` | full | P3-13 |
| `praxis/core/domain/interval_slice_modify.py` | partial | P3-13 |
| `praxis/core/bracket_exit_command_id.py` | full | P3-14, P3-23 |
| `praxis/core/domain/chart_of_accounts.py` | full | P3-11 |
| `praxis/core/domain/journal_entry.py` | partial | P3-11 |
| `praxis/core/domain/trade_pnl.py` | partial | P3-11 |
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
| `praxis/core/domain/bracket_params.py` | partial | P2-21 |
| `praxis/core/domain/iceberg_params.py` | full | P2-22 |
| `praxis/core/plan_even_slices.py` | full | P2-19, P2-20 |
| `praxis/core/plan_weighted_slices.py` | full | P2-19, P2-20 |
| `praxis/infrastructure/event_spine.py` | partial | P2-17, P2-32 |
| `praxis/infrastructure/book_cache.py` | full | P2-26 |
| `praxis/infrastructure/book_poller.py` | full | P2-26 |
| `praxis/core/estimate_slippage.py` | partial | P1-06 |
| `praxis/replay/run_replay.py` | partial | P3-01 |
| `praxis/replay/replay_clock.py` | full | P3-02 |
| `praxis/replay/replay_venue_adapter.py` | partial | P3-03 |
| `praxis/replay/` — the other 7 | uncovered | P3-04 |
| `praxis/binsim/server.py` | partial | P3-05 |
| `praxis/binsim/book.py` | partial | P3-06 |
| `praxis/binsim/feed.py` | partial | P3-06 |
| `praxis/binsim/ledger.py` | partial | P3-07 |
| `praxis/binsim/__main__.py` | partial | P3-05 |
| `praxis/metrics/metric_conventions.py` | full | P3-10 |
| `praxis/metrics/ledger_metrics.py` | partial | P3-10 |
| `praxis/metrics/percentiles.py` | partial | P3-10 |
| `praxis/metrics/` — the other 4 | uncovered | P3-10 |
| `praxis/paper/paper_report.py` | partial | P3-08 |
| `praxis/paper/mark_sampler.py` | partial | P3-09 |
| `praxis/paper/paper_metrics.py` | uncovered | P3-08 |
| the other 59 | uncovered | P3-11 to P3-22 partly |

`execution_manager.py` is 10,867 lines. Ten rows touching it makes it `partial` by a wide margin, not nearly covered.

The articles written so far follow one path: work arriving, being checked, becoming orders, those orders filling, and the outcome going back. Four subsystems have no article at all — replaying recorded bars, the standalone simulated venue, paper-trading reports, and the metrics behind them. The `P3` rows in [the register](register.md) exist to close that.

## Nexus — 81 files

| File | State | Rows |
|---|---|---|
| all 81 | uncovered | — |

Files are listed individually as tracing reaches them. Every untouched file stays listed as `uncovered`. That visibility is the pressure.

---

Created 2026-09-16 09:39 UTC · Last modified 2026-09-30 17:27 UTC
