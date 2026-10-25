# File ledger

Every module in Praxis and Nexus, and whether the wiki accounts for it. A package’s `__init__.py` files are not modules for this purpose and are not counted.

`uncovered` no path walks it · `partial` some behaviour covered · `full` local review accounts for its domain behaviour through reviewed rows or recorded exclusions.

A module reaches `full` only when no unresolved candidate is attached to it. Pending candidates block it.

## Praxis — 88 modules

| File | State | Rows |
|---|---|---|
| `praxis/core/execution_manager.py` | partial | N4-04, P1-01 to P1-13, P2-11 to P2-13, P2-15 to P2-25, P2-27 to P2-29, P2-31, P2-32, P2-34, P2-38, P2-43 to P2-45, P2-49, P3-01 to P3-03, P3-13, P3-14, P3-18, P3-21 to P3-23, P3-25, P3-26, P4-04, P4-06 to P4-12, P4-22, P4-24, P4-27, P4-29, P4-30, P4-33, P4-35, P4-42, P4-44, P4-45, P4-46, P4-47, P4-48, P4-49, P4-50, P4-52, P4-54, P4-56, P4-57, P4-58, P4-59, S-01, S-02, S-03, S-04, S-05 |
| `praxis/core/domain/fill.py` | uncovered | — |
| `praxis/core/account_ledger.py` | partial | N3-12, P2-29, P2-30, P3-11, P3-12, P4-06, P4-12, P4-51 |
| `praxis/core/generate_client_order_id.py` | full | P1-01, P2-24, P3-14, P4-07, P4-33 |
| `praxis/core/validate_trade_modify.py` | partial | P3-13, P4-09, S-03 |
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
| `praxis/core/bracket_exit_command_id.py` | uncovered | — |
| `praxis/core/domain/chart_of_accounts.py` | full | P3-11 |
| `praxis/core/domain/journal_entry.py` | partial | P3-11 |
| `praxis/core/domain/trade_pnl.py` | partial | P3-11 |
| `praxis/core/domain/events.py` | partial | P2-15, P2-33, P4-06, P4-12, P4-33, P4-42, P4-52 |
| `praxis/core/trading_state.py` | partial | N3-10, N4-04, P1-01, P1-07, P2-12, P2-16, P2-19, P2-29 to P2-31, P2-33, P2-49, P3-07, P4-11, P4-12, P4-33, P4-36 |
| `praxis/core/validate_trade_abort.py` | full | P1-04, P4-10 |
| `praxis/core/domain/trade_outcome.py` | partial | P1-04, P2-18, P2-40, P2-42, P2-43 |
| `praxis/infrastructure/binance_adapter.py` | partial | N3-01, N3-12, P1-02, P1-04, P1-07, P1-09, P1-10, P2-11 to P2-14, P2-17, P2-21, P2-22, P2-25, P2-27, P2-28, P2-45, P2-46, P3-14, P3-15, P3-17 to P3-19, P3-21, P3-26, P4-13, P4-45, P4-53, S-01 |
| `praxis/trading.py` | partial | P1-01, P1-04, P1-07, P1-11 to P1-13, P2-11, P2-12, P2-24, P2-25, P2-27, P2-32, P2-46, P3-16, P3-17, P3-18, P3-22, P3-26, P4-06, P4-10, P4-20, P4-22, P4-23, P4-31, P4-32, P4-42, P4-43, P4-44, P4-50, P4-51, P4-55, P4-58, P4-60, S-01, S-03, S-04, S-05 |
| `praxis/trading_inbound.py` | partial | P2-12, P3-19, S-01, S-03, S-04 |
| `praxis/core/validate_trade_command.py` | partial | P2-14, P2-22, P2-24, P2-27, P2-28, P4-04, P4-08, P4-33 |
| `praxis/core/domain/enums.py` | partial | P2-14, P2-18, P2-21, P3-21, P4-04, P4-09, P4-28 |
| `praxis/core/domain/execution_scheme.py` | uncovered | — |
| `praxis/core/domain/ladder_dca_params.py` | full | P2-20 |
| `praxis/core/domain/bracket_params.py` | partial | P4-08 |
| `praxis/core/domain/iceberg_params.py` | full | P2-22 |
| `praxis/core/plan_even_slices.py` | full | P2-19 |
| `praxis/core/plan_weighted_slices.py` | partial | P2-19, P4-08, P4-52 |
| `praxis/infrastructure/event_spine.py` | partial | P2-17, P2-32, P2-35 to P2-37, P3-17, P4-06, P4-30, P4-61 |
| `praxis/infrastructure/book_cache.py` | full | N2-07, P2-26 |
| `praxis/infrastructure/book_poller.py` | full | N2-07, P2-13, P2-26 |
| `praxis/core/estimate_slippage.py` | partial | P1-06, P3-03 |
| `praxis/replay/run_replay.py` | partial | P3-01, P3-02, P3-04, P3-22, P3-24, P4-13, P4-17, P4-39 |
| `praxis/replay/replay_clock.py` | full | P3-02 |
| `praxis/replay/replay_venue_adapter.py` | partial | P2-12, P2-46, P3-03, P3-04, P3-15, P3-18, P4-13 |
| `praxis/replay/replay_scenario.py` | full | P3-04 |
| `praxis/replay/build_replay_report.py` | partial | P3-01, P3-04, P3-08, P3-10, P3-24, P4-18, P4-19 |
| `praxis/replay/replay_report.py` | uncovered | — |
| `praxis/replay/load_replay_bars.py` | full | P4-16, P4-17, P4-39 |
| `praxis/replay/materialize_bar_frames.py` | full | P3-04, P4-39 |
| `praxis/replay/replay_api.py` | full | P4-16, P4-17, P4-40 |
| `praxis/replay/metrics_serialization.py` | full | P3-10, P4-40 |
| `praxis/binsim/server.py` | partial | P2-47, P2-48, P3-05 to P3-07, P3-22 |
| `praxis/binsim/book.py` | partial | P2-48, P3-06 |
| `praxis/binsim/feed.py` | partial | P2-48, P3-06 |
| `praxis/binsim/ledger.py` | partial | P2-47, P3-07 |
| `praxis/binsim/__main__.py` | partial | P3-05, P3-07 |
| `praxis/metrics/metric_conventions.py` | full | P3-10, P4-18 |
| `praxis/metrics/ledger_metrics.py` | partial | P3-10 |
| `praxis/metrics/percentiles.py` | partial | P3-10, P4-18, P4-40 |
| `praxis/metrics/limen_snapshot.py` | full | P4-18, P4-41 |
| `praxis/metrics/snapshot_metrics.py` | partial | P3-10, P4-18 |
| `praxis/metrics/metric_step.py` | full | P4-18 |
| `praxis/metrics/snapshot_result.py` | full | P3-10, P4-18, P4-40 |
| `praxis/paper/paper_report.py` | partial | P3-08, P4-19 |
| `praxis/paper/mark_sampler.py` | partial | P3-09, P4-19 |
| `praxis/paper/paper_metrics.py` | full | P4-18, P4-19 |
| `praxis/launcher.py` | partial | N1-02, N1-03, N1-06, N2-03, N2-05, N2-06, N2-07, N3-01, N3-02, N3-05, N3-06, N3-07, N3-10, N3-12, N4-01, N4-02, N4-05, N4-07, P2-11, P2-13, P2-18, P2-26, P2-32, P2-39, P2-41, P2-43, P2-44, P3-04, P3-08, P3-10, P3-15, P3-16, P3-18, P3-19, P3-20, P3-22, P4-01 to P4-04, P4-06, P4-14, P4-17, P4-20, P4-21, P4-23, P4-25 to P4-27, P4-30, P4-37, P4-39, P4-43, S-04 |
| `praxis/trading_config.py` | partial | P2-24, P3-22, P4-25, P4-42 |
| `praxis/infrastructure/binance_urls.py` | full | P4-03 |
| `praxis/command_translator.py` | partial | P4-04, P4-28 |
| `praxis/outcome_translator.py` | partial | N3-12, N4-02, P2-39, P2-41, P2-43, P4-05, P4-29, P4-30 |
| `praxis/reconciliation_translate.py` | full | P4-06 |
| `praxis/core/domain/trade_command.py` | full | P2-23, P2-24, P2-43, P4-07, P4-08, P4-29, P4-33, P4-36 |
| `praxis/core/domain/_require_str.py` | full | P4-07, P4-09 to P4-12, P4-33 |
| `praxis/core/domain/execution_params.py` | full | P4-08, P4-09, P4-28 |
| `praxis/core/domain/single_shot_params.py` | full | P4-08, P4-09, P4-28 |
| `praxis/core/domain/interval_slice_params.py` | full | P2-19, P4-08 |
| `praxis/core/domain/scheduled_vwap_params.py` | partial | P2-19, P4-08, P4-35 |
| `praxis/core/domain/trade_modify.py` | full | P4-09 |
| `praxis/core/domain/single_shot_modify.py` | full | P4-09, P4-35 |
| `praxis/core/domain/bracket_modify.py` | full | P4-09, P4-35 |
| `praxis/core/domain/iceberg_modify.py` | full | P3-13, P4-09, P4-35 |
| `praxis/core/domain/ladder_dca_modify.py` | full | P3-13, P4-09, P4-35 |
| `praxis/core/domain/scheduled_vwap_modify.py` | full | P4-09, P4-35 |
| `praxis/core/domain/trade_abort.py` | full | P4-10 |
| `praxis/core/domain/order.py` | full | P4-11, P4-36 |
| `praxis/core/domain/position.py` | full | P2-33, P4-12 |
| `praxis/infrastructure/venue_adapter.py` | partial | N2-07, P2-13, P4-13 |
| `praxis/infrastructure/observability.py` | full | P3-20, P4-14, P4-37 |
| `praxis/arrow_price_store.py` | full | P3-04, P4-15, P4-38 |

Every Praxis module is named here: 46 are `full`, 38 `partial` and 4 `uncovered`. A `partial` module has behaviour an article accounts for and behaviour no article reaches yet, or has a question still hanging over it — `execution_manager.py`, at 10,899 lines, is `partial` by the widest margin even with the rows above. The four `uncovered` ones are modules the wiki has written around: a fill's own type, the bracket exit identifier, the scheme parameter type and the replay report's own module each have their behaviour traced through a caller instead, so no row cites the file. Closing those is a later package, and so is the Nexus side the brief also covers.

## Nexus — 70 modules

| File | State | Rows |
|---|---|---|
| `nexus/core/domain/order_types.py` | partial | cited, not traced |
| `nexus/core/capital_controller/capital_controller.py` | partial | N1-01, N1-02, N1-06, N2-01, N2-02, N2-05, N3-02, N3-04, N3-05, N3-06, N3-07, N3-08, N3-09, N3-10, N3-11, N3-12, N4-01, N4-02, N4-05, N4-06 |
| `nexus/core/capital_controller/tracked_order.py` | partial | N4-01 |
| `nexus/core/domain/capital_state.py` | partial | N1-01, N2-02, N3-02, N3-04, N3-05, N3-06, N3-08, N3-09, N4-01, N4-06 |
| `nexus/core/domain/position.py` | partial | N2-01, N2-06, N3-01, N4-03, N4-05 |
| `nexus/core/domain/instance_state.py` | partial | N3-01, N3-02 |
| `nexus/core/domain/risk_state.py` | partial | N2-04, N3-03 |
| `nexus/core/validator/pipeline_executor.py` | partial | N1-03, N1-04, N1-08, N2-06, N3-08, N4-07 |
| `nexus/core/validator/pipeline_models.py` | partial | N1-02, N1-03, N1-04, N3-05, N4-07 |
| `nexus/core/outcome_loop.py` | partial | N1-05, N1-07, N3-07 |
| `nexus/core/health_evaluator.py` | partial | cited, not traced |
| `nexus/core/validator/capital_stage.py` | partial | N1-03, N2-03, N3-08 |
| `nexus/core/validator/health_stage.py` | partial | N2-03 |
| `nexus/core/validator/intake_stage.py` | partial | N2-03, N2-06, N3-05, N4-02, N4-07 |
| `nexus/core/validator/platform_limits_stage.py` | partial | N2-03, N2-06 |
| `nexus/core/validator/risk_stage.py` | partial | N2-03, N2-04 |
| `nexus/core/validator/price_stage.py` | partial | N2-03, N2-07, P2-26 |
| `nexus/core/health_loop.py` | partial | cited, not traced |
| `nexus/core/mode_controller.py` | partial | N2-04, P3-20, P4-43 |
| `nexus/core/domain/bracket_protection_failure_response.py` | full | P4-43 |
| `nexus/core/domain/reconciliation_mismatch_response.py` | full | P4-43 |
| `nexus/reconciler/protection_remediation_handler.py` | full | P4-43 |
| `nexus/reconciler/reconciliation_handler.py` | full | P4-43 |
| `nexus/infrastructure/loss_derivation.py` | partial | N2-03 |
| `nexus/infrastructure/manifest.py` | partial | N3-02, P3-04, P4-26, P4-43 |
| `nexus/infrastructure/wal_codec.py` | partial | N2-02, N3-01, N3-02 |
| `nexus/infrastructure/state_store.py` | partial | N3-03 |
| `nexus/infrastructure/praxis_connector/fund_transaction.py` | partial | cited, not traced |
| `nexus/infrastructure/praxis_connector/outcome_processor.py` | partial | N1-06, N1-07, N2-01, N2-02, N2-06, N3-01, N3-02, N3-03, N3-06, N3-07, N3-09, N3-10, N3-11, N3-12, N4-02, N4-03, N4-05, P3-24, P4-30 |
| `nexus/infrastructure/praxis_connector/praxis_outbound.py` | partial | cited, not traced |
| `nexus/infrastructure/praxis_connector/reconciliation_mismatch.py` | partial | cited, not traced |
| `nexus/infrastructure/praxis_connector/trade_outcome_type.py` | partial | N1-07 |
| `nexus/infrastructure/praxis_connector/translate.py` | partial | cited, not traced |
| `nexus/instance_config.py` | partial | cited, not traced |
| `nexus/startup/sequencer.py` | partial | N3-02, N3-08, N3-10, N3-11, N4-03, P3-04, P4-06 |
| `nexus/startup/shutdown_sequencer.py` | partial | cited, not traced |
| `nexus/strategy/action.py` | partial | N1-08 |
| `nexus/strategy/action_submit.py` | partial | N1-02, N1-08, N2-05, N4-01, N4-02 |
| `nexus/strategy/loader.py` | partial | cited, not traced |
| `nexus/strategy/predict_loop.py` | partial | cited, not traced |
| the other 30 | uncovered | — |

Modules are listed individually as tracing reaches them. Every untouched one stays `uncovered`. That visibility is the pressure.

11 of the modules listed above are `partial` by citation rather than by tracing: a Praxis article or a recorded finding reaches into them for what it needs and cites that, while no row owns the module. The other 29 carry a row — the validator's six stages and the walk that runs them, the money set aside for a trade and what becomes of it, the outcomes that move it on, and the record of how far down the account is. The 41 with no row are the work the packages turn to next, not an exclusion: the brief covers both sides.

---

Created 2026-09-16 09:39 UTC · Last modified 2026-10-23 11:40 UTC
