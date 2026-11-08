# File ledger

Every module in Praxis and Nexus, and whether the wiki accounts for it. A package’s `__init__.py` files are not modules for this purpose and are not counted.

`uncovered` no path walks it · `partial` some behaviour covered · `full` local review accounts for its domain behaviour through reviewed rows or recorded exclusions.

A module reaches `full` only when no unresolved candidate is attached to it. Pending candidates block it.

## Praxis — 88 modules

| File | State | Rows |
|---|---|---|
| `praxis/core/execution_manager.py` | partial | N4-04, N5-03, N5-06, N7-02, N7-05, P1-01, P1-02, P1-03, P1-04, P1-05, P1-06, P1-07, P1-08, P1-09, P1-10, P1-11, P1-12, P1-13, P18-02, P2-11, P2-12, P2-13, P2-15, P2-16, P2-17, P2-18, P2-19, P2-20, P2-21, P2-22, P2-23, P2-24, P2-25, P2-27, P2-28, P2-29, P2-31, P2-32, P2-34, P2-38, P2-43, P2-44, P2-45, P2-49, P3-01, P3-02, P3-03, P3-13, P3-14, P3-18, P3-21, P3-22, P3-23, P3-25, P3-26, P4-04, P4-06, P4-07, P4-08, P4-09, P4-10, P4-11, P4-12, P4-22, P4-24, P4-27, P4-29, P4-30, P4-33, P4-35, P4-42, P4-44, P4-45, P4-46, P4-47, P4-48, P4-49, P4-50, P4-52, P4-54, P4-56, P4-57, P4-58, P4-59, P7-03, P7-04, S-01, S-02, S-03, S-04, S-05 |
| `praxis/core/domain/fill.py` | partial | P7-01, P7-02, P7-03 |
| `praxis/core/account_ledger.py` | partial | N3-12, P2-29, P2-30, P3-11, P3-12, P4-06, P4-12, P4-51 |
| `praxis/core/generate_client_order_id.py` | full | P1-01, P2-24, P3-14, P4-07, P4-33 |
| `praxis/core/validate_trade_modify.py` | partial | P3-13, P4-09, S-03 |
| `praxis/infrastructure/binance_ws.py` | partial | N7-02, P3-16 |
| `praxis/infrastructure/mytrades_backfill.py` | full | P16-01, P3-17 |
| `praxis/core/health_tracker.py` | full | P13-01, P13-02, P3-15 |
| `praxis/infrastructure/token_bucket.py` | full | P3-18, P9-03, P9-04 |
| `praxis/core/classify_submit_failure.py` | full | P3-21 |
| `praxis/infrastructure/secret_store.py` | partial | P3-19, P4-03, P4-26 |
| `praxis/core/live_only_modes.py` | full | P3-22 |
| `praxis/infrastructure/alert_sink.py` | full | P3-20, P8-04 |
| `praxis/core/domain/health_snapshot.py` | full | P3-15, P9-01, P9-02 |
| `praxis/core/domain/modify_params.py` | full | P3-13, P4-09 |
| `praxis/core/domain/interval_slice_modify.py` | full | P3-13, P4-09, P4-35 |
| `praxis/core/bracket_exit_command_id.py` | partial | P7-04 |
| `praxis/core/domain/chart_of_accounts.py` | full | P3-11, P8-01 |
| `praxis/core/domain/journal_entry.py` | full | P3-11 |
| `praxis/core/domain/trade_pnl.py` | partial | P3-11 |
| `praxis/core/domain/events.py` | partial | P2-15, P2-33, P4-06, P4-12, P4-33, P4-42, P4-52, P7-01, P7-03 |
| `praxis/core/trading_state.py` | partial | N3-10, N4-04, N5-03, P1-01, P1-07, P2-12, P2-16, P2-19, P2-29, P2-30, P2-31, P2-33, P2-49, P3-07, P4-11, P4-12, P4-33, P4-36 |
| `praxis/core/validate_trade_abort.py` | full | P1-04, P4-10 |
| `praxis/core/domain/trade_outcome.py` | partial | P1-04, P2-18, P2-40, P2-42, P2-43 |
| `praxis/infrastructure/binance_adapter.py` | partial | N3-01, N3-12, N5-03, N5-06, N7-11, P1-02, P1-04, P1-07, P1-09, P1-10, P16-01, P2-11, P2-12, P2-13, P2-14, P2-17, P2-21, P2-22, P2-25, P2-27, P2-28, P2-45, P2-46, P3-14, P3-15, P3-17, P3-18, P3-19, P3-21, P3-26, P4-13, P4-45, P4-53, S-01 |
| `praxis/trading.py` | partial | N7-02, N7-11, N7-12, P1-01, P1-04, P1-07, P1-11, P1-12, P1-13, P2-11, P2-12, P2-24, P2-25, P2-27, P2-32, P2-46, P3-16, P3-17, P3-18, P3-22, P3-26, P4-06, P4-10, P4-20, P4-22, P4-23, P4-31, P4-32, P4-42, P4-43, P4-44, P4-50, P4-51, P4-55, P4-58, P4-60, S-01, S-03, S-04, S-05 |
| `praxis/trading_inbound.py` | partial | P2-12, P3-19, S-01, S-03, S-04 |
| `praxis/core/validate_trade_command.py` | partial | P2-14, P2-22, P2-24, P2-27, P2-28, P4-04, P4-08, P4-33 |
| `praxis/core/domain/enums.py` | partial | P2-14, P2-18, P2-21, P3-21, P4-04, P4-09, P4-28, N16-06 |
| `praxis/core/domain/execution_scheme.py` | partial | P7-06 |
| `praxis/core/domain/ladder_dca_params.py` | full | P10-01, P10-02, P18-02, P2-20 |
| `praxis/core/domain/bracket_params.py` | partial | P4-08 |
| `praxis/core/domain/iceberg_params.py` | full | P2-22 |
| `praxis/core/plan_even_slices.py` | full | P10-03, P16-02, P2-19 |
| `praxis/core/plan_weighted_slices.py` | full | P18-02, P2-19, P4-08, P4-52 |
| `praxis/infrastructure/event_spine.py` | partial | P2-17, P2-32, P2-35, P2-36, P2-37, P3-17, P4-06, P4-30, P4-61 |
| `praxis/infrastructure/book_cache.py` | full | N2-07, P2-26 |
| `praxis/infrastructure/book_poller.py` | full | N2-07, P11-01, P11-02, P11-03, P2-13, P2-26 |
| `praxis/core/estimate_slippage.py` | partial | P1-06, P3-03 |
| `praxis/replay/run_replay.py` | partial | N9-01, N9-02, N9-05, P3-01, P3-02, P3-04, P3-22, P3-24, P4-13, P4-17, P4-39 |
| `praxis/replay/replay_clock.py` | full | P3-02, P8-03 |
| `praxis/replay/replay_venue_adapter.py` | partial | P2-12, P2-46, P3-03, P3-04, P3-15, P3-18, P4-13 |
| `praxis/replay/replay_scenario.py` | full | P3-04 |
| `praxis/replay/build_replay_report.py` | partial | P15-03, P3-01, P3-04, P3-08, P3-10, P3-24, P4-18, P4-19 |
| `praxis/replay/replay_report.py` | partial | P7-06 |
| `praxis/replay/load_replay_bars.py` | full | P14-01, P15-03, P4-16, P4-17, P4-39 |
| `praxis/replay/materialize_bar_frames.py` | full | P3-04, P4-39 |
| `praxis/replay/replay_api.py` | full | P14-01, P14-02, P4-16, P4-17, P4-40 |
| `praxis/replay/metrics_serialization.py` | full | P3-10, P4-40 |
| `praxis/binsim/server.py` | partial | P2-47, P2-48, P3-05, P3-06, P3-07, P3-22 |
| `praxis/binsim/book.py` | partial | P2-48, P3-06 |
| `praxis/binsim/feed.py` | partial | P2-48, P3-06 |
| `praxis/binsim/ledger.py` | partial | P2-47, P3-07 |
| `praxis/binsim/__main__.py` | partial | P3-05, P3-07 |
| `praxis/metrics/metric_conventions.py` | full | P3-10, P4-18 |
| `praxis/metrics/ledger_metrics.py` | full | P3-10 |
| `praxis/metrics/percentiles.py` | partial | P3-10, P4-18, P4-40 |
| `praxis/metrics/limen_snapshot.py` | full | P12-01, P12-02, P12-03, P12-04, P15-01, P15-02, P15-03, P4-18, P4-41 |
| `praxis/metrics/snapshot_metrics.py` | partial | P3-10, P4-18 |
| `praxis/metrics/metric_step.py` | full | P4-18 |
| `praxis/metrics/snapshot_result.py` | full | P3-10, P4-18, P4-40 |
| `praxis/paper/paper_report.py` | partial | P3-08, P4-19 |
| `praxis/paper/mark_sampler.py` | partial | P3-09, P4-19 |
| `praxis/paper/paper_metrics.py` | full | P4-18, P4-19 |
| `praxis/launcher.py` | partial | N1-02, N1-03, N1-06, N2-03, N2-05, N2-06, N2-07, N3-01, N3-02, N3-05, N3-06, N3-07, N3-10, N3-12, N4-01, N4-02, N4-05, N4-07, N5-02, N6-01, N6-04, N6-05, N6-06, N6-08, N6-09, N6-11, N7-02, N7-03, N7-04, N7-05, N7-07, N7-10, N7-11, N7-12, N8-03, N8-05, N8-06, N8-07, N9-01, N9-02, N9-04, N9-05, P11-03, P2-11, P2-13, P2-18, P2-26, P2-32, P2-39, P2-41, P2-43, P2-44, P3-04, P3-08, P3-10, P3-15, P3-16, P3-18, P3-19, P3-20, P3-22, P4-01, P4-02, P4-03, P4-04, P4-06, P4-14, P4-17, P4-20, P4-21, P4-23, P4-25, P4-26, P4-27, P4-30, P4-37, P4-39, P4-43, P5-01, P5-02, P5-05, P5-06, P5-07, P6-01, P6-04, P7-04, S-04 |
| `praxis/trading_config.py` | partial | P2-24, P3-22, P4-25, P4-42 |
| `praxis/infrastructure/binance_urls.py` | full | P4-03 |
| `praxis/command_translator.py` | partial | P4-04, P4-28 |
| `praxis/outcome_translator.py` | partial | N3-12, N4-02, P2-39, P2-41, P2-43, P4-05, P4-29, P4-30 |
| `praxis/reconciliation_translate.py` | full | P4-06 |
| `praxis/core/domain/trade_command.py` | full | P2-23, P2-24, P2-43, P4-07, P4-08, P4-29, P4-33, P4-36, P8-01 |
| `praxis/core/domain/_require_str.py` | full | P4-07, P4-09, P4-10, P4-11, P4-12, P4-33, P7-01, P8-02 |
| `praxis/core/domain/execution_params.py` | full | P4-08, P4-09, P4-28 |
| `praxis/core/domain/single_shot_params.py` | full | P4-08, P4-09, P4-28 |
| `praxis/core/domain/interval_slice_params.py` | full | P2-19, P4-08 |
| `praxis/core/domain/scheduled_vwap_params.py` | partial | P18-02, P2-19, P4-08, P4-35 |
| `praxis/core/domain/trade_modify.py` | full | P4-09 |
| `praxis/core/domain/single_shot_modify.py` | full | P4-09, P4-35 |
| `praxis/core/domain/bracket_modify.py` | full | P4-09, P4-35 |
| `praxis/core/domain/iceberg_modify.py` | full | P3-13, P4-09, P4-35 |
| `praxis/core/domain/ladder_dca_modify.py` | full | P3-13, P4-09, P4-35 |
| `praxis/core/domain/scheduled_vwap_modify.py` | full | P4-09, P4-35 |
| `praxis/core/domain/trade_abort.py` | full | P4-10 |
| `praxis/core/domain/order.py` | full | P4-11, P4-36, P8-01 |
| `praxis/core/domain/position.py` | full | P2-33, P4-12, P8-01 |
| `praxis/infrastructure/venue_adapter.py` | partial | N2-07, P2-13, P4-13 |
| `praxis/infrastructure/observability.py` | full | P3-20, P4-14, P4-37, P7-05 |
| `praxis/arrow_price_store.py` | full | N7-11, P3-04, P4-15, P4-38, P8-03 |

Every Praxis module is named here: 49 are `full` and 39 `partial`, with none `uncovered`. A `partial` module has behaviour an article accounts for and behaviour no article reaches yet, or has a question still hanging over it — `execution_manager.py`, at 10,899 lines, is `partial` by the widest margin even with the rows above. The four that were `uncovered` are now reached by package 7: the bracket exit identifier, the scheme projection and the replay report had their behaviour traced through a caller and now carry rows of their own, and a fill's own type — which has no caller, nothing outside the tests building one — carries three.

## Nexus — 70 modules

| File | State | Rows |
|---|---|---|
| `nexus/core/domain/order_types.py` | full | N16-06, P4-04 |
| `nexus/core/capital_controller/capital_controller.py` | partial | N1-01, N1-02, N1-06, N2-01, N2-02, N2-05, N3-02, N3-04, N3-05, N3-06, N3-07, N3-08, N3-09, N3-10, N3-11, N3-12, N4-01, N4-02, N4-05, N4-06, N5-01, N5-02, N7-02, N7-10, P6-03, P6-04 |
| `nexus/core/capital_controller/reservation.py` | partial | N13-01, N13-02, N13-03, N13-07, N15-08 |
| `nexus/core/domain/risk_breaker_thresholds.py` | full | N14-07, N18-04 |
| `nexus/core/capital_controller/tracked_order.py` | partial | N4-01, N5-02 |
| `nexus/core/domain/capital_state.py` | partial | N1-01, N2-02, N3-02, N3-04, N3-05, N3-06, N3-08, N3-09, N4-01, N4-06, N7-10, P5-04 |
| `nexus/core/domain/position.py` | partial | N2-01, N2-06, N3-01, N4-03, N4-05, N6-02 |
| `nexus/core/domain/instance_state.py` | partial | N3-01, N3-02, N7-08, P5-04 |
| `nexus/core/domain/risk_state.py` | partial | N19-01, N2-04, N3-03, N7-09, P18-01 |
| `nexus/core/validator/pipeline_executor.py` | partial | N1-03, N1-04, N1-08, N2-06, N3-08, N4-07 |
| `nexus/core/validator/pipeline_models.py` | partial | N1-02, N1-03, N1-04, N3-05, N4-07, N5-06, N6-10, N16-01 |
| `nexus/core/outcome_loop.py` | partial | N1-05, N1-07, N3-07, N6-05, N6-07, N6-09, N6-11, N10-02, N10-06 |
| `nexus/core/health_evaluator.py` | full | N15-01, N15-02, N15-03, N15-04, N15-05, P3-15, P9-02 |
| `nexus/core/validator/capital_stage.py` | partial | N1-03, N2-03, N3-08, P6-04 |
| `nexus/core/validator/health_stage.py` | partial | N19-02, N2-03 |
| `nexus/core/validator/intake_stage.py` | partial | N2-03, N2-06, N3-05, N4-02, N4-07, N5-06, N6-01, N6-10, N7-03, N7-10, N8-06, N8-07 |
| `nexus/core/validator/platform_limits_stage.py` | partial | N2-03, N2-06 |
| `nexus/core/validator/risk_stage.py` | full | N19-01, N19-02, N2-03, N2-04 |
| `nexus/core/validator/price_stage.py` | partial | N2-03, N2-07, P2-26 |
| `nexus/core/health_loop.py` | partial | N6-01, N6-11, N15-05, N15-06, P3-15 |
| `nexus/core/mode_controller.py` | partial | N2-04, N6-01, N7-09, N8-03, P3-20, P4-43, N15-06 |
| `nexus/core/domain/operational_mode.py` | partial | N6-01, N15-07, N15-08 |
| `nexus/core/domain/bracket_protection_failure_response.py` | full | P4-43 |
| `nexus/core/domain/reconciliation_mismatch_response.py` | full | P4-43 |
| `nexus/reconciler/protection_remediation_handler.py` | full | P4-43 |
| `nexus/reconciler/reconciliation_handler.py` | full | P4-43 |
| `nexus/core/mtm_loop.py` | partial | N6-01, N6-11, N8-03 |
| `nexus/infrastructure/loss_derivation.py` | full | N15-08, N2-03, N7-09 |
| `nexus/infrastructure/manifest.py` | partial | N3-02, N6-02, N7-03, N7-10, P3-04, P4-26, P4-43 |
| `nexus/infrastructure/wal_codec.py` | partial | N2-02, N3-01, N3-02, N7-08, N8-03, N9-04 |
| `nexus/infrastructure/state_store.py` | partial | N3-03, N7-02, N7-08, N7-09, N8-01, N8-03, N9-02, N9-04, P18-01, P5-01, P5-06, P5-07, P6-01, P6-04 |
| `nexus/infrastructure/snapshot.py` | full | N7-08, N7-09, N8-03, N8-04, N9-04, P18-01 |
| `nexus/infrastructure/wal.py` | partial | N7-08, N7-09, N8-01, N8-02, N8-03, N8-04, N8-08, N9-03 |
| `nexus/infrastructure/wal_entry.py` | full | N18-02, N8-08 |
| `nexus/infrastructure/snapshot_scheduler.py` | partial | N6-01, N6-11, N7-08, N7-12, N8-05, N9-01 |
| `nexus/infrastructure/praxis_connector/fund_transaction.py` | full | N16-04, P4-06 |
| `nexus/infrastructure/praxis_connector/outcome_processor.py` | partial | N1-06, N1-07, N2-01, N2-02, N2-06, N3-01, N3-02, N3-03, N3-06, N3-07, N3-09, N3-10, N3-11, N3-12, N4-02, N4-03, N4-05, N7-05, N7-09, N9-04, P3-24, P4-30, P6-03, P7-04 |
| `nexus/infrastructure/praxis_connector/praxis_inbound.py` | full | N16-06, N6-04 |
| `nexus/infrastructure/praxis_connector/praxis_outbound.py` | partial | N11-02, N6-06, N6-08, N6-09, N7-02, N7-05, P4-04, P4-06 |
| `nexus/infrastructure/praxis_connector/process_result.py` | full | N18-01, N9-04 |
| `nexus/infrastructure/praxis_connector/order_context.py` | partial | N13-04, N13-05, N13-06 |
| `nexus/infrastructure/praxis_connector/protection_remediation.py` | full | N14-06 |
| `nexus/infrastructure/praxis_connector/reconciliation_mismatch.py` | full | N16-05, P4-06 |
| `nexus/infrastructure/praxis_connector/trade_command_type.py` | full | N11-01, N16-02 |
| `nexus/infrastructure/praxis_connector/trade_command.py` | partial | N11-01, N11-02, N11-03, N11-04, N14-04, N15-08, N16-02, P8-02 |
| `nexus/infrastructure/praxis_connector/trade_outcome.py` | full | N12-01, N12-02, N12-03, N12-04, N15-08, P8-02 |
| `nexus/infrastructure/praxis_connector/trade_outcome_type.py` | full | N1-07, N18-03, N7-05 |
| `nexus/infrastructure/praxis_connector/translate.py` | full | N16-01, N16-02, N16-03, N5-04, N5-06, P4-04 |
| `nexus/instance_config.py` | full | N17-01, N17-02, N17-03, N17-04, N17-05, P4-04 |
| `nexus/startup/sequencer.py` | partial | N3-02, N3-08, N3-10, N3-11, N4-03, N5-05, N7-07, N7-08, N9-01, N9-02, N9-05, P3-04, P4-06, P5-03, P5-04, P5-06, N10-01, N10-02, N10-06 |
| `nexus/startup/shutdown_sequencer.py` | partial | N1-08, N3-02, N4-02, N4-07, N5-04, N5-06, N6-01, N6-02, N6-03, N6-04, N6-05, N6-07, N6-08, N6-10, N7-01, N7-02, N7-08, N7-12, N9-01, N10-02 |
| `nexus/strategy/action.py` | partial | N1-08, N6-03, N6-05, N7-03, N7-11 |
| `nexus/strategy/action_submit.py` | partial | N1-02, N1-08, N2-05, N4-01, N4-02, N5-02, N5-04, N5-06, N6-08, N6-09, N6-10, N7-03, N7-04, N7-05 |
| `nexus/strategy/loader.py` | full | N17-06, N17-07, P4-17 |
| `nexus/strategy/predict_loop.py` | partial | N7-06, P3-04, P4-39, N10-02, N10-06 |
| `nexus/strategy/runner.py` | partial | N10-01, N10-04 |
| `nexus/strategy/executor.py` | full | N10-01 |
| `nexus/infrastructure/observability.py` | partial | P7-05 |
| `nexus/infrastructure/strategy_event.py` | full | N14-01, N14-02 |
| `nexus/strategy/base.py` | partial | N10-03 |
| `nexus/strategy/params.py` | full | N14-04, N14-05, N17-02 |
| `nexus/strategy/signal.py` | full | N14-03, N14-04, N17-02, N18-04 |
| `nexus/strategy/timer_loop.py` | partial | N10-02, N10-05, N10-06 |
| `nexus/strategy/context.py` | partial | N10-06 |
| `nexus/core/capital_controller/lifecycle_result.py` | full | shape only; no behaviour to trace |
| `nexus/core/domain/enums.py` | full | shape only; no behaviour to trace |
| `nexus/core/stp_mode.py` | full | shape only; no behaviour to trace |
| `nexus/infrastructure/praxis_connector/inbound_connector.py` | full | shape only; no behaviour to trace |
| `nexus/infrastructure/praxis_connector/outbound_connector.py` | full | shape only; no behaviour to trace |
| `nexus/startup/error.py` | full | shape only; no behaviour to trace |

Modules are listed individually as tracing reaches them, and every one of Nexus's 70 is now listed. Six are marked `full` as shapes: five sets of named values across three of them, two shapes a connector must answer to, a record of how a lifecycle call went, and two error types. Each declares names or a shape, or keeps what it was handed, and makes no check of its own, so there is no behaviour for an article to trace; a value outside one of those sets is refused by the machinery the set is built on rather than by anything in the module. Package 7 recorded that, and it is an exclusion rather than work outstanding.

6 of the modules listed above carry no row of their own, and all six are the shapes recorded below. Every other Nexus module is owned by at least one row: the eight that were `partial` by citation alone were taken by packages 15, 16 and 17. The other 64 carry a row — the validator's six stages and the walk that runs them, the money set aside for a trade and what becomes of it, the outcomes that move it on, and the record of how far down the account is. The 6 with no row are the shapes below, an exclusion rather than work outstanding. What remains on this side is depth: of the 64 that carry a row, 26 are accounted for in full and 38 are not.

---

Created 2026-09-16 09:39 UTC · Last modified 2026-11-10 23:00 UTC
