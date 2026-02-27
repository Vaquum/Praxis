# Changelog

## v0.1.0 on 23rd of February, 2026

- Add Binance Spot testnet connectivity verification tests in [`tests/testnet/`](tests/testnet/)
- Add [`conftest.py`](tests/testnet/conftest.py) with constants, auth helpers, skip markers, and dotenv support
- Add [`test_safety.py`](tests/testnet/test_safety.py) for URL sanity checks
- Add [`test_rest_public.py`](tests/testnet/test_rest_public.py) for unauthenticated REST endpoint tests
- Add [`test_rest_auth.py`](tests/testnet/test_rest_auth.py) for authenticated REST endpoint tests
- Add [`test_websocket.py`](tests/testnet/test_websocket.py) for WebSocket connectivity and E2E fill tests
- Add `aiohttp`, `websockets`, `pytest-asyncio`, and `python-dotenv` as dev dependencies
- Add `.env` support for testnet credential loading
- Add CI pipeline with Ruff, Mypy strict, pytest, and CodeQL workflows
- Configure strict Ruff linting rules in [`pyproject.toml`](pyproject.toml)
- Configure strict Mypy in [`pyproject.toml`](pyproject.toml)
- Exclude testnet tests from default `pytest` collection via `addopts`
- Update README with setup instructions, testnet verification guide, and integrations
- Remove template `docs/Developer/` placeholder

## v0.2.0 on 24th of February, 2026

- Add `structlog>=24.1` and `orjson>=3.10` as runtime dependencies
- Add [`observability.py`](praxis/infrastructure/observability.py) with `configure_logging`, `bind_context`, `clear_context`, `get_logger`
- Add `praxis/infrastructure/` package
- Add stdlib logging integration through structlog `ProcessorFormatter`
- Add asyncio-safe context variable binding for `epoch_id`, `account_id`, `command_id`, `client_order_id`, `event_seq`
- Add [`test_observability.py`](tests/test_observability.py) with 10 tests covering JSON output, context binding, level filtering, and stdlib integration
- Add `praxis-journals/` to `.gitignore`
- Remove placeholder test file `tests/test_placeholder.py`

## v0.3.0 on 24th of February, 2026

- Add `praxis/core/domain/` package with `Position`, `Order`, `Fill` dataclasses
- Add `OrderSide`, `OrderType`, `OrderStatus` enums in [`enums.py`](praxis/core/domain/enums.py)
- Add frozen `Fill` dataclass with `dedup_key` property per RFC fill deduplication spec
- Add mutable `Order` dataclass with `is_terminal` and `remaining_qty` properties
- Add mutable `Position` dataclass with `is_closed` property
- Add domain package re-exports in `praxis/core/domain/__init__.py`
- Add [`test_domain_core.py`](tests/test_domain_core.py) with 36 tests covering enums, dataclass creation, immutability, properties, Decimal precision, and construction-time validation

## v0.4.0 on 25th of February, 2026

- Add `ExecutionMode`, `MakerPreference`, `STPMode` enums in [`enums.py`](praxis/core/domain/enums.py)
- Add frozen `SingleShotParams` dataclass with positive price validation in [`single_shot_params.py`](praxis/core/domain/single_shot_params.py)
- Add frozen `TradeCommand` dataclass with qty, timeout, price, and timezone validation in [`trade_command.py`](praxis/core/domain/trade_command.py)
- Add frozen `TradeAbort` dataclass with timezone-aware validation in [`trade_abort.py`](praxis/core/domain/trade_abort.py)
- Add domain package re-exports for all 12 domain types in `praxis/core/domain/__init__.py`
- Add [`test_domain_commands.py`](tests/test_domain_commands.py) with 28 tests covering enums, dataclass creation, immutability, Decimal precision, and construction-time validation
- Refactor zero/negative validation tests into parametrized functions across both test files

## v0.5.0 on 25th of February, 2026

- Add `TradeStatus` enum with terminal and non-terminal execution states in [`enums.py`](praxis/core/domain/enums.py)
- Add frozen `TradeOutcome` dataclass with `is_terminal` and `fill_ratio` properties in [`trade_outcome.py`](praxis/core/domain/trade_outcome.py)
- Add construction-time validation for target_qty, filled_qty, avg_fill_price, slices, missed_iterations, and timezone-aware created_at
- Add domain package re-exports for all 14 domain types in `praxis/core/domain/__init__.py`
- Add [`test_domain_outcome.py`](tests/test_domain_outcome.py) with 29 tests covering enum membership, dataclass creation, immutability, properties, Decimal precision, and construction-time validation

## v0.6.0 on 25th of February, 2026

- Add 10 frozen event dataclasses (`CommandAccepted`, `OrderSubmitIntent`, `OrderSubmitted`, `OrderSubmitFailed`, `OrderAcked`, `FillReceived`, `OrderRejected`, `OrderCanceled`, `OrderExpired`, `TradeClosed`) with `Event` type alias in [`events.py`](praxis/core/domain/events.py)
- Add `_EventBase` base class with shared `account_id` and timezone-aware `timestamp` validation
- Add non-empty string validation via `_require_str` helper on all event identifier fields
- Add `TradingState` projection class with `apply()` dispatch, VWAP position tracking, and order lifecycle management in [`trading_state.py`](praxis/core/trading_state.py)
- Add `TradingState` re-export from `praxis.core` package
- Add domain package re-exports for all 25 domain types in `praxis/core/domain/__init__.py`
- Add [`test_trading_state.py`](tests/test_trading_state.py) with 27 tests covering construction validation, apply dispatch, order lifecycle, position VWAP, exit fills, warning logs, and full lifecycle

## v0.6.1 on 26th of February, 2026
- Add non-empty string validation to `Position` (`account_id`, `trade_id`, `symbol`), `Order` (`client_order_id`, `account_id`, `command_id`, `symbol`), `Fill` (`venue_order_id`, `client_order_id`, `account_id`, `trade_id`, `command_id`, `symbol`, `fee_asset`), `TradeCommand` (`command_id`, `trade_id`, `account_id`, `symbol`), `TradeAbort` (`command_id`, `account_id`, `reason`), and `TradeOutcome` (`command_id`, `trade_id`, `account_id`)
- Add parametrized empty-string validation tests to [`test_domain_core.py`](tests/test_domain_core.py), [`test_domain_commands.py`](tests/test_domain_commands.py), and [`test_domain_outcome.py`](tests/test_domain_outcome.py)
- Add `__post_init__` docstrings to `TradeCommand` and `TradeOutcome` for consistency with other domain dataclasses
- Add `.claude/` to `.gitignore`
- Refactor `events.py` to import `_require_str` from shared module instead of defining it locally

## v0.7.0 on 26th of February, 2026

- Add `aiosqlite>=0.20` as runtime dependency
- Add `EventSpine` class in [`event_spine.py`](praxis/infrastructure/event_spine.py) with append-only SQLite event log, epoch-scoped reads, and event type registry hydration
- Add `append()` method serializing domain events via orjson with Decimal, datetime, and enum support
- Add `read()` method hydrating stored payloads back into domain Event dataclasses via `get_type_hints`-based coercion
- Add `last_event_seq()` method returning highest sequence number per epoch
- Add [`test_event_spine.py`](tests/test_event_spine.py) with 19 tests covering round-trip for all 10 event types, epoch isolation, ordering, Decimal precision, datetime timezone, enum preservation, and after_seq filtering

## v0.8.0 on 26th of February, 2026

- Add `fill_dedup` table with `UNIQUE(epoch_id, account_id, dedup_key)` constraint for epoch-scoped fill deduplication in [`event_spine.py`](praxis/infrastructure/event_spine.py)
- Add fill deduplication to `EventSpine.append()` — duplicate `FillReceived` events silently dropped per RFC, scoped by (account_id, venue_trade_id) per epoch
- Add `PLR2004` to test file ruff ignores in [`pyproject.toml`](pyproject.toml)
- Add 7 fill deduplication tests to [`test_event_spine.py`](tests/test_event_spine.py) covering duplicate detection, cross-account correctness, epoch scoping, and non-fill event passthrough
- Harden `_hydrate` forward-compatibility by filtering payload keys against declared type hints, silently ignoring extra fields from older event schemas
- Add [`docs/TechnicalDebt.md`](docs/TechnicalDebt.md) tracking 5 known debt items (TD-001 through TD-005) mined from PR review history
