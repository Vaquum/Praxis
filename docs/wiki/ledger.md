# File ledger

Every module in Praxis and Nexus, and whether the wiki accounts for it. A package’s `__init__.py` files are not modules for this purpose and are not counted.

`uncovered` no path walks it · `partial` some behaviour covered · `covered` local review accounts for its domain behaviour through reviewed rows or recorded exclusions.

A file reaches `covered` only when no unresolved candidate is attached to it. Pending candidates block it.

## Praxis — 88 modules

| File | State | Rows |
|---|---|---|
| `praxis/core/execution_manager.py` | partial | P1-01 to P1-10, P2-11 to P2-25 |
| `praxis/core/domain/fill.py` | full | P2-15 |
| `praxis/core/account_ledger.py` | partial | P2-16, P2-29, P3-11, P3-12 |
| `praxis/core/generate_client_order_id.py` | full | P3-14 |
| `praxis/core/validate_trade_modify.py` | partial | P3-13, P4-09 |
| `praxis/infrastructure/binance_ws.py` | partial | P3-16 |
| `praxis/infrastructure/mytrades_backfill.py` | full | P3-17 |
| `praxis/core/health_tracker.py` | full | P3-15 |
| `praxis/infrastructure/token_bucket.py` | full | P3-18 |
| `praxis/core/classify_submit_failure.py` | full | P3-21 |
| `praxis/infrastructure/secret_store.py` | partial | P3-19, P4-03, P4-26 |
| `praxis/core/live_only_modes.py` | full | P3-22 |
| `praxis/infrastructure/alert_sink.py` | full | P3-20 |
| `praxis/core/domain/health_snapshot.py` | full | P3-15 |
| `praxis/core/domain/modify_params.py` | full | P3-13, P4-09 |
| `praxis/core/domain/interval_slice_modify.py` | full | P3-13, P4-09, P4-35 |
| `praxis/core/bracket_exit_command_id.py` | full | P3-14, P3-23 |
| `praxis/core/domain/chart_of_accounts.py` | full | P3-11 |
| `praxis/core/domain/journal_entry.py` | partial | P3-11 |
| `praxis/core/domain/trade_pnl.py` | partial | P3-11 |
| `praxis/core/domain/events.py` | partial | P2-15 |
| `praxis/core/trading_state.py` | partial | P1-01 |
| `praxis/core/validate_trade_abort.py` | full | P1-04, P4-10 |
| `praxis/core/domain/trade_outcome.py` | full | P1-04, P2-18 |
| `praxis/infrastructure/binance_adapter.py` | partial | P1-07, P1-10, P2-11, P2-25 |
| `praxis/trading.py` | partial | P2-11, P2-12, P4-06, P4-20, P4-22, P4-23, P4-31, P4-32 |
| `praxis/trading_inbound.py` | partial | P2-12 |
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
| `praxis/replay/run_replay.py` | partial | P3-01, P3-04, P3-24 |
| `praxis/replay/replay_clock.py` | full | P3-02 |
| `praxis/replay/replay_venue_adapter.py` | partial | P2-12, P3-03 |
| `praxis/replay/replay_scenario.py` | full | P3-04 |
| `praxis/replay/build_replay_report.py` | partial | P3-10, P3-24 |
| `praxis/replay/replay_report.py` | partial | P3-24 |
| `praxis/replay/load_replay_bars.py` | full | P4-16 |
| `praxis/replay/materialize_bar_frames.py` | full | P4-39 |
| `praxis/replay/replay_api.py` | full | P4-17, P4-40 |
| `praxis/replay/metrics_serialization.py` | full | P4-40 |
| `praxis/binsim/server.py` | partial | P3-05 |
| `praxis/binsim/book.py` | partial | P3-06 |
| `praxis/binsim/feed.py` | partial | P3-06 |
| `praxis/binsim/ledger.py` | partial | P3-07 |
| `praxis/binsim/__main__.py` | partial | P3-05 |
| `praxis/metrics/metric_conventions.py` | full | P3-10 |
| `praxis/metrics/ledger_metrics.py` | partial | P3-10 |
| `praxis/metrics/percentiles.py` | partial | P3-10 |
| `praxis/metrics/limen_snapshot.py` | full | P3-10, P4-41 |
| `praxis/metrics/snapshot_metrics.py` | partial | P3-10, P4-18 |
| `praxis/metrics/metric_step.py` | full | P4-18 |
| `praxis/metrics/snapshot_result.py` | full | P4-18 |
| `praxis/paper/paper_report.py` | partial | P3-08 |
| `praxis/paper/mark_sampler.py` | partial | P3-09 |
| `praxis/paper/paper_metrics.py` | full | P3-08, P4-19 |
| `praxis/launcher.py` | partial | P3-20, P3-22, P4-01, P4-02, P4-03, P4-20, P4-21, P4-25, P4-26, P4-27 |
| `praxis/trading_config.py` | partial | P4-03, P4-25 |
| `praxis/infrastructure/binance_urls.py` | full | P4-03 |
| `praxis/command_translator.py` | partial | P4-04, P4-28 |
| `praxis/outcome_translator.py` | full | P4-05, P4-29, P4-30 |
| `praxis/reconciliation_translate.py` | full | P4-06 |
| `praxis/core/domain/trade_command.py` | full | P2-24, P4-07, P4-33 |
| `praxis/core/domain/_require_str.py` | full | P4-07, P4-33 |
| `praxis/core/domain/execution_params.py` | full | P4-08, P4-28 |
| `praxis/core/domain/single_shot_params.py` | full | P4-08, P4-28 |
| `praxis/core/domain/interval_slice_params.py` | full | P4-08 |
| `praxis/core/domain/scheduled_vwap_params.py` | full | P4-08 |
| `praxis/core/domain/trade_modify.py` | full | P3-13, P4-09 |
| `praxis/core/domain/single_shot_modify.py` | full | P4-09, P4-35 |
| `praxis/core/domain/bracket_modify.py` | full | P4-09, P4-35 |
| `praxis/core/domain/iceberg_modify.py` | full | P4-09, P4-35 |
| `praxis/core/domain/ladder_dca_modify.py` | full | P4-09, P4-35 |
| `praxis/core/domain/scheduled_vwap_modify.py` | full | P4-09, P4-35 |
| `praxis/core/domain/trade_abort.py` | full | P4-10, P4-24 |
| `praxis/core/domain/order.py` | full | P4-11, P4-36 |
| `praxis/core/domain/position.py` | full | P4-12 |
| `praxis/infrastructure/venue_adapter.py` | partial | P4-13 |
| `praxis/infrastructure/observability.py` | full | P4-14, P4-37 |
| `praxis/arrow_price_store.py` | full | P4-15, P4-38 |

`execution_manager.py` is 10,867 lines. Ten rows touching it makes it `partial` by a wide margin, not nearly covered.

Every Praxis file is now named here. The four subsystems that had no article — replaying recorded bars, the standalone simulated venue, paper-trading reports, and the metrics behind them — each have one, and the `P4` rows in [the register](register.md) carry the files still marked `uncovered`: the host itself, the seams between Nexus and Praxis, the shapes a request is carried in, and the leaves the earlier rows stopped short of.

## Nexus — 70 modules

| File | State | Rows |
|---|---|---|
| all 70 | uncovered | — |

Files are listed individually as tracing reaches them. Every untouched file stays listed as `uncovered`. That visibility is the pressure.

---

Created 2026-09-16 09:39 UTC · Last modified 2026-10-04 06:29 UTC
