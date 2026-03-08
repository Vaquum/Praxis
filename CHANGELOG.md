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

## v0.9.0 on 27th of February, 2026

- Add `VenueAdapter` runtime-checkable `Protocol` with 8 async methods (`submit_order`, `cancel_order`, `query_order`, `query_open_orders`, `query_balance`, `query_trades`, `get_exchange_info`, `get_server_time`) in [`venue_adapter.py`](praxis/infrastructure/venue_adapter.py)
- Add 7 frozen response dataclasses (`ImmediateFill`, `SubmitResult`, `CancelResult`, `VenueOrder`, `VenueTrade`, `BalanceEntry`, `SymbolFilters`) in [`venue_adapter.py`](praxis/infrastructure/venue_adapter.py)
- Add `VenueError` base exception with 5 typed subclasses (`OrderRejectedError`, `RateLimitError`, `AuthenticationError`, `TransientError`, `NotFoundError`) in [`venue_adapter.py`](praxis/infrastructure/venue_adapter.py)
- Add `VenueTrade.__post_init__` timezone validation matching codebase pattern (`Fill`, `_EventBase`, `TradeCommand`)
- Add `account_id` parameter to all authenticated Protocol methods for multi-account API key routing
- Add docstring notes for `cancel_order` and `query_order` requiring at least one order identifier
- Rename `SubmitResult.fills` to `immediate_fills` with corrected docstring
- Add [`test_venue_adapter.py`](tests/test_venue_adapter.py) with 24 tests covering dataclass immutability, timestamp validation, error hierarchy, pickle safety, and Protocol conformance

## v0.10.0 on 28th of February, 2026

- Add `BinanceAdapter` class in [`binance_adapter.py`](praxis/infrastructure/binance_adapter.py) implementing `VenueAdapter.submit_order()` via Binance `POST /api/v3/order` with `newOrderRespType=FULL`
- Add HMAC-SHA256 request signing and `X-MBX-APIKEY` header authentication
- Add order parameter building for `OrderType.MARKET`, `OrderType.LIMIT`, and `OrderType.LIMIT_IOC` with automatic `timeInForce` handling and Decimal serialization
- Add response normalization mapping Binance statuses to `OrderStatus` and fills to `ImmediateFill` tuple
- Add HTTP error mapping: 400 → `OrderRejectedError`, 401 → `AuthenticationError`, 403/418/429 → `RateLimitError`, 5xx → `TransientError`
- Add credential management via constructor injection with runtime `register_account`/`unregister_account`
- Add async context manager session lifecycle with explicit `close()`
- Move `aiohttp>=3.10` from dev to runtime dependencies in [`pyproject.toml`](pyproject.toml)
- Add [`test_binance_adapter.py`](tests/test_binance_adapter.py) with 47 unit tests covering credentials, signing, param building, status mapping, response parsing, error handling, session lifecycle, and end-to-end submit flow
- Add [`tests/testnet/test_binance_adapter.py`](tests/testnet/test_binance_adapter.py) with 3 testnet integration tests for market buy (filled), limit resting (open), and limit IOC (expired)

## v0.11.0 on 1st of March, 2026

- Add `_signed_request` helper extracting auth and dispatch from `submit_order` in [`binance_adapter.py`](praxis/infrastructure/binance_adapter.py)
- Add `_map_order_type` mapping Binance `type`/`timeInForce` strings to `OrderType` and `_parse_venue_order` response-to-`VenueOrder` helper in [`binance_adapter.py`](praxis/infrastructure/binance_adapter.py)
- Add `cancel_order` via `DELETE /api/v3/order` in [`binance_adapter.py`](praxis/infrastructure/binance_adapter.py)
- Add `query_order` via `GET /api/v3/order` in [`binance_adapter.py`](praxis/infrastructure/binance_adapter.py)
- Add `query_open_orders` via `GET /api/v3/openOrders` in [`binance_adapter.py`](praxis/infrastructure/binance_adapter.py)
- Add `query_balance` via `GET /api/v3/account` with asset filtering in [`binance_adapter.py`](praxis/infrastructure/binance_adapter.py)
- Add `assets: frozenset[str]` parameter to `VenueAdapter.query_balance` Protocol in [`venue_adapter.py`](praxis/infrastructure/venue_adapter.py)
- Add `NotFoundError` mapping for Binance error codes -2013 and -2011 in [`binance_adapter.py`](praxis/infrastructure/binance_adapter.py)
- Refactor `_signed_request` return type from `dict[str, Any]` to `Any` to support array responses
- Add 25 unit tests for `_signed_request`, `cancel_order`, `query_order`, `query_open_orders`, and `query_balance` in [`test_binance_adapter.py`](tests/test_binance_adapter.py)
- Add 4 testnet integration tests for cancel, query order, query open orders, and query balance in [`tests/testnet/test_binance_adapter.py`](tests/testnet/test_binance_adapter.py)

## v0.12.0 on 2nd of March, 2026

- Add `STOP_LOSS`, `STOP_LOSS_LIMIT`, `TAKE_PROFIT`, `TAKE_PROFIT_LIMIT`, `LIMIT_MAKER`, and `OCO` mappings to `_map_order_type` via `_BINANCE_TYPE_MAP` lookup in [`binance_adapter.py`](praxis/infrastructure/binance_adapter.py)
- Add `LIMIT`+`FOK` handling mapping to `OrderType.LIMIT_IOC` in `_map_order_type` in [`binance_adapter.py`](praxis/infrastructure/binance_adapter.py)
- Add transient HTTP retry with exponential backoff and full jitter in `_signed_request` in [`binance_adapter.py`](praxis/infrastructure/binance_adapter.py)
- Add `_parse_venue_trade` helper mapping Binance `myTrades` entries to `VenueTrade` with Decimal precision, UTC timestamps, and `isMaker` in [`binance_adapter.py`](praxis/infrastructure/binance_adapter.py)
- Add `query_trades` via `GET /api/v3/myTrades` with optional timezone-aware `start_time` filter in [`binance_adapter.py`](praxis/infrastructure/binance_adapter.py)
- Refactor `_map_order_type` from chained if-statements to dict lookup to satisfy `PLR0911` in [`binance_adapter.py`](praxis/infrastructure/binance_adapter.py)
- Fix testnet `test_query_balance_returns_requested_assets` assertions to run inside context manager in [`tests/testnet/test_binance_adapter.py`](tests/testnet/test_binance_adapter.py)
- Add 8 unit tests for new `_map_order_type` mappings in [`test_binance_adapter.py`](tests/test_binance_adapter.py)
- Add `test_empty_assets_skips_api_call` verifying `query_balance` short-circuits without API call in [`test_binance_adapter.py`](tests/test_binance_adapter.py)
- Add 7 unit tests for retry success, exhaustion, non-retryable errors, sleep delay, and log output in [`test_binance_adapter.py`](tests/test_binance_adapter.py)
- Add 9 unit tests for `_parse_venue_trade` and `query_trades` covering field mapping, Decimal precision, UTC timestamps, `isMaker`, `startTime` conversion, and naive datetime rejection in [`test_binance_adapter.py`](tests/test_binance_adapter.py)

## v0.13.0 on 4th of March, 2026

- Add `get_exchange_info` method parsing `PRICE_FILTER`, `LOT_SIZE`, and `NOTIONAL` from unauthenticated `GET /api/v3/exchangeInfo` in [`binance_adapter.py`](praxis/infrastructure/binance_adapter.py)
- Add `load_filters` startup method for explicit per-symbol filter caching in [`binance_adapter.py`](praxis/infrastructure/binance_adapter.py)
- Add `_validate_order` helper checking lot step, lot range, tick size, and min notional with graceful degradation when filters not cached in [`binance_adapter.py`](praxis/infrastructure/binance_adapter.py)
- Add pre-submission validation in `submit_order` before `_build_order_params` in [`binance_adapter.py`](praxis/infrastructure/binance_adapter.py)
- Add 13 unit tests for `get_exchange_info`, `load_filters`, and `_validate_order` in [`test_binance_adapter.py`](tests/test_binance_adapter.py)

## v0.14.0 on 5th of March, 2026

- Add `retry_after` field to `RateLimitError` and parse `Retry-After` header in [`venue_adapter.py`](praxis/infrastructure/venue_adapter.py)
- Add `_DEFAULT_WEIGHT_LIMIT`, `_DEFAULT_ORDER_COUNT_LIMIT`, and `_RATE_LIMIT_WARN_THRESHOLD` constants in [`binance_adapter.py`](praxis/infrastructure/binance_adapter.py)
- Add `_update_weight_from_headers` parsing `X-MBX-USED-WEIGHT-1M` and `X-MBX-ORDER-COUNT-10S` with per-account order count tracking in [`binance_adapter.py`](praxis/infrastructure/binance_adapter.py)
- Add `_parse_rate_limits` extracting `REQUEST_WEIGHT` and `ORDERS` limits from `exchangeInfo` response in [`binance_adapter.py`](praxis/infrastructure/binance_adapter.py)
- Add `RateLimitError` retry with `Retry-After` support in `_signed_request` in [`binance_adapter.py`](praxis/infrastructure/binance_adapter.py)
- Add `weight_headroom` property and `order_count_headroom` method returning normalized 0.0–1.0 headroom in [`binance_adapter.py`](praxis/infrastructure/binance_adapter.py)
- Add unit tests for rate limit state tracking, header parsing, retry, and headroom in [`test_binance_adapter.py`](tests/test_binance_adapter.py)
- Add unit tests for `RateLimitError` fields in [`test_venue_adapter.py`](tests/test_venue_adapter.py)

## v0.15.0 on 6th of March, 2026

- Add `OrderBookLevel` and `OrderBookSnapshot` frozen dataclasses to [`venue_adapter.py`](praxis/infrastructure/venue_adapter.py)
- Add `query_order_book` to `VenueAdapter` protocol with default limit=20 in [`venue_adapter.py`](praxis/infrastructure/venue_adapter.py)
- Implement `query_order_book` in `BinanceAdapter` via unauthenticated `GET /api/v3/depth` with response parsing and weight tracking in [`binance_adapter.py`](praxis/infrastructure/binance_adapter.py)
- Add unit tests for order book parsing, error handling, weight tracking, and immutability in [`test_binance_adapter.py`](tests/test_binance_adapter.py)

## v0.16.0 on 6th of March, 2026

- Add `_api_key_request` helper for API-key-only REST calls without HMAC signing in [`binance_adapter.py`](praxis/infrastructure/binance_adapter.py)
- Add `_create_listen_key`, `_keepalive_listen_key`, and `_close_listen_key` methods for user data stream lifecycle in [`binance_adapter.py`](praxis/infrastructure/binance_adapter.py)
- Add `BinanceUserStream` class with connect, close, keepalive loop, `_listen` dispatch, and async context manager in [`binance_ws.py`](praxis/infrastructure/binance_ws.py)
- Add `on_message` callback dispatch in `_listen()` with JSON parsing, non-JSON skip, callback error resilience, and CLOSED/ERROR break in [`binance_ws.py`](praxis/infrastructure/binance_ws.py)
- Add 9 unit tests for `_api_key_request` and listen key methods in [`test_binance_adapter.py`](tests/test_binance_adapter.py)
- Add 18 unit tests for `BinanceUserStream` covering URL building, connect/close lifecycle, keepalive, context manager, and `_listen` dispatch in [`test_binance_ws.py`](tests/test_binance_ws.py)
- Add TD-007 tracking duplicated retry loop between `_signed_request` and `_api_key_request` in [`TechnicalDebt.md`](docs/TechnicalDebt.md)

## v0.17.0 on 8th of March, 2026

- Add `ExecutionType` enum (NEW, TRADE, CANCELED, REPLACED, REJECTED, EXPIRED, TRADE_PREVENTION) to [`enums.py`](praxis/core/domain/enums.py)
- Add `ExecutionReport` frozen dataclass with 19 typed fields and timezone-aware validation to [`venue_adapter.py`](praxis/infrastructure/venue_adapter.py)
- Add `_BINANCE_EXECUTION_TYPE_MAP` constant and `_parse_execution_report` method mapping single-letter Binance keys to domain types in [`binance_adapter.py`](praxis/infrastructure/binance_adapter.py)
- Add 14 unit tests for execution report parsing covering trade fill, NEW/CANCELED/REJECTED/EXPIRED/TRADE_PREVENTION, market order, unknown value errors, decimal precision, and UTC timestamps in [`test_binance_adapter.py`](tests/test_binance_adapter.py)

## v0.18.0 on 9th of March, 2026

- Add `reconnect_base_delay` and `reconnect_max_delay` config params to `BinanceUserStream.__init__` in [`binance_ws.py`](praxis/infrastructure/binance_ws.py)
- Add `_clean_setup_connection` method extracting teardown + connect logic from `initiate_connection` in [`binance_ws.py`](praxis/infrastructure/binance_ws.py)
- Add `_auto_reconnect` method with exponential backoff, jitter, and infinite retry on disconnect in [`binance_ws.py`](praxis/infrastructure/binance_ws.py)
- Wire `initiate_connection` to start `_reconnect_task` running `_auto_reconnect`, `close` to cancel it in [`binance_ws.py`](praxis/infrastructure/binance_ws.py)
- Rename `_listen` to `_receive_loop` and `connect` to `initiate_connection` for clearer client/server nomenclature in [`binance_ws.py`](praxis/infrastructure/binance_ws.py)
- Add 4 unit tests for auto-reconnect, exponential backoff, attempt reset, and cancel-during-backoff in [`test_binance_ws.py`](tests/test_binance_ws.py)
