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

## v0.19.0 on 9th of March, 2026

- Add `MAINNET_REST_URL`, `MAINNET_WS_URL`, `TESTNET_REST_URL`, `TESTNET_WS_URL` public constants to [`binance_adapter.py`](praxis/infrastructure/binance_adapter.py)
- Add `ws_base_url` parameter to `BinanceAdapter.__init__` for independent REST and WS URL configuration in [`binance_adapter.py`](praxis/infrastructure/binance_adapter.py)
- Refactor `BinanceUserStream._build_ws_url` to use `_ws_base_url` directly, removing broken `https→wss` scheme-swap hack in [`binance_ws.py`](praxis/infrastructure/binance_ws.py)
- Update testnet conftest to import URL constants from production code instead of duplicating them in [`conftest.py`](tests/testnet/conftest.py)
- Update all unit and testnet tests for new `BinanceAdapter` constructor signature in [`test_binance_adapter.py`](tests/test_binance_adapter.py), [`test_binance_ws.py`](tests/test_binance_ws.py), [`tests/testnet/test_binance_adapter.py`](tests/testnet/test_binance_adapter.py)

## v0.20.0 on 9th of March, 2026

- Add `ExecutionManager` class with per-account unbounded command and priority queues in [`execution_manager.py`](praxis/core/execution_manager.py)
- Add `_AccountRuntime` internal class holding per-account queue pair, `TradingState` projection, and asyncio task in [`execution_manager.py`](praxis/core/execution_manager.py)
- Add `register_account` and `unregister_account` methods with coroutine lifecycle management in [`execution_manager.py`](praxis/core/execution_manager.py)
- Add `submit_command` method with UUID generation, `CommandAccepted` event persistence, and queue routing in [`execution_manager.py`](praxis/core/execution_manager.py)
- Add `submit_abort` method enqueuing `TradeAbort` to per-account priority queue in [`execution_manager.py`](praxis/core/execution_manager.py)
- Add `_account_loop` coroutine draining priority queue before command queue on each iteration in [`execution_manager.py`](praxis/core/execution_manager.py)
- Add `AccountNotRegisteredError` exception for unregistered account_id targeting in [`execution_manager.py`](praxis/core/execution_manager.py)
- Add `_QUEUE_POLL_INTERVAL` constant for account loop poll timeout in [`execution_manager.py`](praxis/core/execution_manager.py)
- Add `ExecutionManager` and `AccountNotRegisteredError` re-exports from `praxis.core` package in [`__init__.py`](praxis/core/__init__.py)
- Add [`test_execution_manager.py`](tests/test_execution_manager.py) with 13 tests covering registration, unregistration, command submission, abort submission, priority drain ordering, and account isolation

## v0.21.0 on 9th of March, 2026

- Add `generate_client_order_id` pure function producing deterministic `{prefix}-{hex16}-{seq}[rN]` client order IDs for venue submission in [`generate_client_order_id.py`](praxis/core/generate_client_order_id.py)
- Add `_MODE_PREFIX` mapping all 7 `ExecutionMode` variants to 2-character prefixes (SS, BK, TW, SV, IC, TD, LD) in [`generate_client_order_id.py`](praxis/core/generate_client_order_id.py)
- Add UUID4 truncation to first 16 hex characters (64-bit entropy) for Binance 36-character `newClientOrderId` limit in [`generate_client_order_id.py`](praxis/core/generate_client_order_id.py)
- Add `generate_client_order_id` re-export from `praxis.core` package in [`__init__.py`](praxis/core/__init__.py)
- Add [`test_generate_client_order_id.py`](tests/test_generate_client_order_id.py) with 27 tests covering all mode prefixes, format, sequence padding, retry suffix, length validation, and error cases

## v0.22.0 on 10th of March, 2026

- Add `validate_trade_command` inbound validator with mode/order-type gating, SingleShot parameter coherence checks, maker-only compatibility checks, and optional venue filter checks in [`validate_trade_command.py`](praxis/core/validate_trade_command.py)
- Add `validate_trade_abort` inbound validator with unknown-command rejection, account ownership checks, and terminal-command no-op behavior in [`validate_trade_abort.py`](praxis/core/validate_trade_abort.py)
- Add `validate_trade_command` and `validate_trade_abort` re-exports from the core package in [`__init__.py`](praxis/core/__init__.py)
- Update `ExecutionManager.submit_command` and `ExecutionManager.submit_abort` with inbound validation and accepted/terminal command ID tracking in [`execution_manager.py`](praxis/core/execution_manager.py)
- Add [`test_validate_trade_abort.py`](tests/test_validate_trade_abort.py) with 8 tests covering valid abort, unknown command_id, terminal no-op, and account_id mismatch
- Add [`test_validate_trade_command.py`](tests/test_validate_trade_command.py) with 83 tests covering allowed/disallowed mode-order pairs, SingleShot param requirements, maker preference rules, and venue filter boundaries
- Add integration tests to [`test_execution_manager.py`](tests/test_execution_manager.py) for inbound validation rejection/no-op behavior and accepted command tracking

## v0.22.1 on 10th of March, 2026

- Fix 66 mypy strict-mode errors across 5 test files by adding `dict[str, Any]` annotations, `-> None` return types, `Event` type alias usage, and `bool()` wrapper in [`test_domain_commands.py`](tests/test_domain_commands.py), [`test_domain_core.py`](tests/test_domain_core.py), [`test_domain_outcome.py`](tests/test_domain_outcome.py), [`test_event_spine.py`](tests/test_event_spine.py), [`conftest.py`](tests/testnet/conftest.py)

## v0.23.0 on 10th of March, 2026

- Add `venue_adapter: VenueAdapter` parameter to `ExecutionManager.__init__` for venue order submission in [`execution_manager.py`](praxis/core/execution_manager.py)
- Add `_process_command` method with deterministic client order ID generation, `OrderSubmitIntent` persistence for crash durability, venue submission via `VenueAdapter.submit_order`, `OrderSubmitted` and `FillReceived` event persistence with fill deduplication, and `OrderSubmitFailed` on `VenueError` in [`execution_manager.py`](praxis/core/execution_manager.py)
- Add `_process_command` call in `_account_loop` after command dequeue in [`execution_manager.py`](praxis/core/execution_manager.py)
- Add 9 `TestProcessCommand` tests covering market fill, limit no-fill, venue rejection, transient failure, multiple fills, fill deduplication, client order ID determinism, trading state projection, and loop resilience in [`test_execution_manager.py`](tests/test_execution_manager.py)

## v0.24.0 on 11th of March, 2026

- Add `TradeOutcomeProduced` frozen event dataclass with `command_id`, `trade_id`, `status`, and `reason` fields in [`events.py`](praxis/core/domain/events.py)
- Add `TradeOutcomeProduced` to `Event` type alias and `__all__` in [`events.py`](praxis/core/domain/events.py)
- Add `TradeOutcomeProduced` handler with debug logging in `TradingState.apply()` in [`trading_state.py`](praxis/core/trading_state.py)
- Add `TradeOutcomeProduced` to `_EVENT_REGISTRY` for hydration in [`event_spine.py`](praxis/infrastructure/event_spine.py)
- Add `on_trade_outcome: Callable[[TradeOutcome], Awaitable[None]] | None` parameter to `ExecutionManager.__init__` in [`execution_manager.py`](praxis/core/execution_manager.py)
- Add `_build_outcome` method constructing `TradeOutcome`, emitting `TradeClosed` for terminal outcomes with fills and `TradeOutcomeProduced` for all outcomes, and invoking the async callback in [`execution_manager.py`](praxis/core/execution_manager.py)
- Add filled quantity summation, VWAP computation, overfill clamping, and status determination (`FILLED`, `PARTIAL`, `PENDING`, `REJECTED`) to `_process_command` in [`execution_manager.py`](praxis/core/execution_manager.py)
- Add 8 `TestTradeOutcome` tests covering callback delivery, rejected with reason, pending, partial fill, VWAP computation, no-callback, field correctness, and spine event verification in [`test_execution_manager.py`](tests/test_execution_manager.py)
- Add `test_overfill_clamped_with_correct_vwap` test asserting clamped `filled_qty` and VWAP computed from unclamped fills in [`test_execution_manager.py`](tests/test_execution_manager.py)
- Rename `test_trading_state_has_position_after_fill` to `test_trading_state_has_closed_order_after_fill` in [`test_execution_manager.py`](tests/test_execution_manager.py)
- Fix missing `_terminal_commands` tracking for terminal outcomes in `_build_outcome` in [`execution_manager.py`](praxis/core/execution_manager.py)
- Fix `TradeClosed` emission to skip terminal outcomes with zero fills in `_build_outcome` in [`execution_manager.py`](praxis/core/execution_manager.py)
- Fix VWAP inflated on overfill by computing `avg_fill_price` before clamping `filled_qty` in [`execution_manager.py`](praxis/core/execution_manager.py)
- Fix unguarded `on_trade_outcome` callback propagating exceptions into account loop in [`execution_manager.py`](praxis/core/execution_manager.py)
- Fix import ordering for `collections.abc` in [`execution_manager.py`](praxis/core/execution_manager.py)
- Fix `reason=str(exc)` producing tuple-like strings for `OrderRejectedError` by using `exc.args[0]` in [`execution_manager.py`](praxis/core/execution_manager.py)
- Update 9 existing `TestProcessCommand` test assertions for `TradeClosed` and `TradeOutcomeProduced` event sequences in [`test_execution_manager.py`](tests/test_execution_manager.py)

## v0.25.0 on 11th of March, 2026

- Add `_deadline_at` and `_deadline_exceeded` deadline computation helpers in [`execution_manager.py`](praxis/core/execution_manager.py)
- Add timeout enforcement transitioning non-terminal statuses (`PENDING`, `PARTIAL`) to `EXPIRED` with `reason='deadline exceeded'` in `_process_command` in [`execution_manager.py`](praxis/core/execution_manager.py)
- Add order expiry eventing on timeout with `cancel_order` call, `OrderExpired` event emission on cancel success or `NotFoundError`, and `cancel_confirmed=False` fallback on other `VenueError` in [`execution_manager.py`](praxis/core/execution_manager.py)
- Add 8 `TestDeadlineHandling` tests covering pending expiry, partial fill expiry, `TradeOutcomeProduced` with EXPIRED status, `OrderExpired` emission, `NotFoundError` fallback, `VenueError` skip, terminal abort no-op, and non-expired control case in [`test_execution_manager.py`](tests/test_execution_manager.py)
- Fix `_TS` test constant from `datetime(2026, 1, 1)` to `datetime(2099, 1, 1)` preventing false deadline triggers in existing tests in [`test_execution_manager.py`](tests/test_execution_manager.py)

## v0.26.0 on 11th of March, 2026

- Add `_commands` and `_aborted_commands` state to `ExecutionManager.__init__` for abort command lookup and pre-submission tracking in [`execution_manager.py`](praxis/core/execution_manager.py)
- Add `_process_abort` method with venue cancel dispatch, `OrderCanceled` emission on success or `NotFoundError`, VWAP-preserving `CANCELED` outcome, and pre-submission marker fallback in [`execution_manager.py`](praxis/core/execution_manager.py)
- Add `_process_abort` call with error guard in `_account_loop` priority queue drain in [`execution_manager.py`](praxis/core/execution_manager.py)
- Add pre-submission abort guard in `_process_command` short-circuiting to `CANCELED` without venue call in [`execution_manager.py`](praxis/core/execution_manager.py)
- Add 5 `TestProcessAbort` tests covering pending order abort, partial fill VWAP preservation, `NotFoundError` resilience, `VenueError` cancel failure, and pre-submission short-circuit in [`test_execution_manager.py`](tests/test_execution_manager.py)

## v0.27.0 on 12th of March, 2026

- Add mode dispatch guard in `_process_command` rejecting unsupported `ExecutionMode` with `REJECTED` outcome instead of raising `NotImplementedError` in [`execution_manager.py`](praxis/core/execution_manager.py)
- Add `stop_limit_price: Decimal | None` field to `OrderSubmitIntent` with positive-value validation in [`events.py`](praxis/core/domain/events.py)
- Add `stop_limit_price` passthrough from `SingleShotParams` through `OrderSubmitIntent` to `VenueAdapter.submit_order` in [`execution_manager.py`](praxis/core/execution_manager.py)
- Add `stop_limit_price` keyword parameter to `VenueAdapter.submit_order` protocol in [`venue_adapter.py`](praxis/infrastructure/venue_adapter.py)
- Add `_BINANCE_OCO_STATUS_MAP` constant mapping Binance OCO list statuses (`EXECUTING`, `REJECT`) to `OrderStatus` in [`binance_adapter.py`](praxis/infrastructure/binance_adapter.py)
- Add `_build_oco_params` helper building Binance `POST /api/v3/order/oco` request parameters with symbol, side, qty, price, stopPrice, stopLimitPrice, and listClientOrderId in [`binance_adapter.py`](praxis/infrastructure/binance_adapter.py)
- Add `_parse_oco_response` helper extracting `orderListId` as venue_order_id, mapping `listOrderStatus`, and collecting fills from both `orderReports` in [`binance_adapter.py`](praxis/infrastructure/binance_adapter.py)
- Add OCO order dispatch in `submit_order` routing `OrderType.OCO` to `/api/v3/order/oco` with dedicated params builder and response parser in [`binance_adapter.py`](praxis/infrastructure/binance_adapter.py)
- Add `TestModeDispatch` test verifying unsupported mode produces `REJECTED` outcome via callback in [`test_execution_manager.py`](tests/test_execution_manager.py)
- Add `TestStopLimitPassthrough` test verifying `stop_limit_price` flows from params to `OrderSubmitIntent` and `venue_adapter.submit_order` in [`test_execution_manager.py`](tests/test_execution_manager.py)
- Add 3 `TestBuildOcoParams` tests covering required params, stop_limit_price inclusion, and client_order_id mapping in [`test_binance_adapter.py`](tests/test_binance_adapter.py)
- Add 3 `TestParseOcoResponse` tests covering EXECUTING→OPEN mapping, ALL_DONE with fills, and unknown list status rejection in [`test_binance_adapter.py`](tests/test_binance_adapter.py)
- Add 3 `TestSubmitOcoOrder` tests covering OCO endpoint dispatch, missing price rejection, and missing stop_price rejection in [`test_binance_adapter.py`](tests/test_binance_adapter.py)
- Add `cancel_order_list` method to `VenueAdapter` protocol for OCO list cancellation via `DELETE /api/v3/orderList` in [`venue_adapter.py`](praxis/infrastructure/venue_adapter.py)
- Add `cancel_order_list` implementation with `orderListId` and `listClientOrderId` dispatch in [`binance_adapter.py`](praxis/infrastructure/binance_adapter.py)
- Add OCO-aware cancel routing in `_process_abort` and `_process_command` deadline path branching on `OrderType.OCO` to call `cancel_order_list` in [`execution_manager.py`](praxis/core/execution_manager.py)
- Add `time_in_force` parameter to `_build_oco_params` defaulting to `GTC` instead of hardcoding in [`binance_adapter.py`](praxis/infrastructure/binance_adapter.py)
- Fix `is_maker` in `_parse_oco_response` reading `isMaker` from Binance OCO fill payloads instead of hardcoding `False` in [`binance_adapter.py`](praxis/infrastructure/binance_adapter.py)
- Fix `ALL_DONE` status derivation in `_parse_oco_response` deriving from leg statuses instead of mapping directly to `FILLED` in [`binance_adapter.py`](praxis/infrastructure/binance_adapter.py)
- Add `TestOcoAbortRouting` test verifying OCO abort calls `cancel_order_list` instead of `cancel_order` in [`test_execution_manager.py`](tests/test_execution_manager.py)
- Add 3 `TestCancelOrderList` tests covering `orderListId` dispatch, `listClientOrderId` dispatch, and missing-both rejection in [`test_binance_adapter.py`](tests/test_binance_adapter.py)
- Add `TestBuildOcoParams::test_time_in_force_passed_through` test in [`test_binance_adapter.py`](tests/test_binance_adapter.py)
- Add `TestParseOcoResponse::test_all_done_canceled_no_fills` test verifying `ALL_DONE` with only canceled legs produces `CANCELED` status in [`test_binance_adapter.py`](tests/test_binance_adapter.py)
- Add `TestParseOcoResponse::test_is_maker_read_from_payload` test in [`test_binance_adapter.py`](tests/test_binance_adapter.py)

## v0.28.0 on 12th of March, 2026

- Add `SlippageEstimate` dataclass and `estimate_slippage` pure function with walk-the-book VWAP and bps computation in [`estimate_slippage.py`](praxis/core/estimate_slippage.py)
- Add pre-submission slippage estimation in `_process_command` with order book query (`limit=20`) and non-fatal fallback logging on estimation/query failures in [`execution_manager.py`](praxis/core/execution_manager.py)
- Add post-fill slippage logging in `_process_command` for `execution_slippage_bps` (vs estimated mid-price) and conditional `arrival_slippage_bps` (vs `reference_price`) in [`execution_manager.py`](praxis/core/execution_manager.py)
- Add slippage-focused `ExecutionManager` tests for estimate logging, order-book-query failure fallback, execution slippage logging, and arrival slippage logging in [`test_execution_manager_slippage.py`](tests/test_execution_manager_slippage.py)
- Add `estimate_slippage` and `SlippageEstimate` re-exports in [`__init__.py`](praxis/core/__init__.py)

## v0.29.0 on 13th of March, 2026

- Add `register_account(account_id, api_key, api_secret)` and `unregister_account(account_id)` methods to `VenueAdapter` protocol in [`venue_adapter.py`](praxis/infrastructure/venue_adapter.py)
- Add `TradingInbound` service providing basic inbound account registration orchestration with hardcoded account credential mapping in [`trading_inbound.py`](praxis/trading_inbound.py)
- Add rollback behavior in `TradingInbound.register_account` to remove venue credentials when execution account registration fails in [`trading_inbound.py`](praxis/trading_inbound.py)
- Add `TradingInbound` tests covering happy path, unknown credentials, empty account id rejection, rollback behavior, and unregister orchestration in [`test_trading_inbound.py`](tests/test_trading_inbound.py)
- Add protocol conformance coverage for the new account registration methods in [`test_venue_adapter.py`](tests/test_venue_adapter.py)

## v0.30.0 on 13th of March, 2026

- Add inbound `TradingInbound.submit_command(...)` handler routing directly to execution manager command intake in [`trading_inbound.py`](praxis/trading_inbound.py)
- Add inbound `TradingInbound.submit_abort(...)` handler routing directly to execution manager abort intake in [`trading_inbound.py`](praxis/trading_inbound.py)
- Add `_ExecutionInboundGateway` protocol support for `submit_command` and `submit_abort` routing contracts in [`trading_inbound.py`](praxis/trading_inbound.py)
- Add inbound routing tests for command pass-through, abort pass-through, and execution-error propagation in [`test_trading_inbound.py`](tests/test_trading_inbound.py)

## v0.31.0 on 14th of March, 2026

- Add `ExecutionManager.pull_positions(account_id)` for detached per-account positions snapshot pulls in [`execution_manager.py`](praxis/core/execution_manager.py)
- Add `TradingInbound.pull_positions(account_id)` and `_ExecutionInboundGateway` protocol support for positions pull routing in [`trading_inbound.py`](praxis/trading_inbound.py)
- Add positions pull boundary tests for execution snapshot semantics and inbound routing/error propagation in [`test_execution_manager_pull_positions.py`](tests/test_execution_manager_pull_positions.py) and [`test_trading_inbound.py`](tests/test_trading_inbound.py)
- Add callback contract tests asserting one callback await per produced outcome and non-blocking behavior on callback exceptions in [`test_execution_manager_trade_outcome_callback.py`](tests/test_execution_manager_trade_outcome_callback.py)
- Update `ExecutionManager` callback contract documentation for async invocation ordering and exception suppression in [`execution_manager.py`](praxis/core/execution_manager.py)

## v0.32.0 on 15th of March, 2026

- Add `TradingConfig` MMVP runtime wiring surface and export it from package root in [`trading_config.py`](praxis/trading_config.py) and [`__init__.py`](praxis/__init__.py)
- Add `Trading` composition root that wires Event Spine, venue adapter, execution manager, and inbound facade in [`trading.py`](praxis/trading.py)
- Add basic MMVP lifecycle supervision to `Trading` with readiness gate and managed-account cleanup via `start()`/`stop()` in [`trading.py`](praxis/trading.py)
- Add focused tests for config validation/defaults, composition wiring, facade delegation, and lifecycle cleanup/no-leaked account tasks in [`test_trading_config.py`](tests/test_trading_config.py) and [`test_trading.py`](tests/test_trading.py)

## v0.33.0 on 15th of March, 2026

- Add startup sequencing with per-account phases in `Trading.start()` orchestrating replay, filters, WebSocket, and reconciliation in [`trading.py`](praxis/trading.py)
- Add `ExecutionManager.replay_events(account_id, events)` rebuilding trading state and runtime indices from event spine in [`execution_manager.py`](praxis/core/execution_manager.py)
- Add `ExecutionManager.active_symbols(account_id)` returning symbols with open orders for filter preloading in [`execution_manager.py`](praxis/core/execution_manager.py)
- Add `VenueAdapter.load_filters(symbols)` protocol method for batch exchange info preloading in [`venue_adapter.py`](praxis/infrastructure/venue_adapter.py)
- Add WebSocket user stream wiring routing `executionReport` messages to domain event flow via `BinanceUserStream` in [`trading.py`](praxis/trading.py)
- Add basic venue reconciliation querying live order/trade state and emitting correction events for diverged projections in [`trading.py`](praxis/trading.py)
- Add per-account readiness gating rejecting commands/aborts while account startup is in progress in [`trading.py`](praxis/trading.py)
- Add startup and readiness gating tests covering replay, filter preload, WebSocket wiring, and command rejection in [`test_trading.py`](tests/test_trading.py)

## v0.34.0 on 16th of March, 2026

- Add graceful shutdown sequence in `Trading.stop()` with cancel-orders, wait-for-terminal, close-streams phases in [`trading.py`](praxis/trading.py)
- Add `_stopping` flag gating command/abort rejection during shutdown in [`trading.py`](praxis/trading.py)
- Add `ExecutionManager.get_open_orders(account_id)` returning open orders snapshot for shutdown cancellation in [`execution_manager.py`](praxis/core/execution_manager.py)
- Add `TradingConfig.shutdown_timeout` config field for terminal-state wait timeout in [`trading_config.py`](praxis/trading_config.py)
- Add shutdown sequence tests covering command rejection, abort rejection, and order cancellation in [`test_trading.py`](tests/test_trading.py)

## v0.35.0 on 16th of March, 2026

- Add shared `spine` fixture in [`tests/conftest.py`](tests/conftest.py) for test harness consolidation
- Remove duplicate `spine` fixture definitions from 6 test files

## v0.36.0 on 16th of March, 2026

- Remove dead `TradeStatus.PAUSED` enum member and docstring reference from [`enums.py`](praxis/core/domain/enums.py)
- Add 26 tests for startup reconciliation (`_reconcile_account`, `_reconcile_fills`, `_reconcile_terminal`) and WebSocket handler (`_on_execution_report`, `_convert_execution_report`) in [`test_trading.py`](tests/test_trading.py)
- Update `test_domain_outcome.py` to reflect PAUSED removal from `_NON_TERMINAL` list and `test_trade_status_members` expected set

## v0.37.0 on 7th of April, 2026

- Add `ws_event_queue` to `_AccountRuntime` for routing WebSocket events through account coroutine in [`execution_manager.py`](praxis/core/execution_manager.py)
- Add `enqueue_ws_event(account_id, event)` method for single-writer compliant event routing in [`execution_manager.py`](praxis/core/execution_manager.py)
- Add SAVEPOINT wrapper around dual-INSERT (dedup + event) for `FillReceived` atomicity in [`event_spine.py`](praxis/infrastructure/event_spine.py)
- Add `_build_abort_outcome` method for abort-specific outcome building from Order data in [`execution_manager.py`](praxis/core/execution_manager.py)
- Add `__setattr__` guards to `Order` validating `qty > 0` and `filled_qty >= 0` in [`order.py`](praxis/core/domain/order.py)
- Add `__setattr__` guards to `Position` validating `qty >= 0` and `avg_entry_price >= 0` in [`position.py`](praxis/core/domain/position.py)
- Add `cumulative_notional` field to `Order` tracking running total of fill_qty × fill_price in [`order.py`](praxis/core/domain/order.py)
- Refactor `_process_abort` to compute VWAP from `order.cumulative_notional / filled_qty` instead of spine re-read in [`execution_manager.py`](praxis/core/execution_manager.py)
- Update `_account_loop` to drain `ws_event_queue` before processing commands in [`execution_manager.py`](praxis/core/execution_manager.py)
- Update `_on_execution_report` to enqueue events instead of applying directly in [`trading.py`](praxis/trading.py)
- Update `_reconcile_fills` and `_reconcile_terminal` to enqueue events instead of applying directly in [`trading.py`](praxis/trading.py)
- Update `_process_abort` to use `Order` fields from `TradingState` instead of `_commands` lookup in [`execution_manager.py`](praxis/core/execution_manager.py)
- Update `TradingState` to clamp negative position qty to 0 after warning in [`trading_state.py`](praxis/core/trading_state.py)
- Update `TradingState._update_order_on_fill` to accumulate notional on each fill in [`trading_state.py`](praxis/core/trading_state.py)
- Add concurrency tests proving single-writer model prevents corruption in [`test_trading.py`](tests/test_trading.py)
- Add atomicity test proving SAVEPOINT rollback on event insert failure in [`test_event_spine.py`](tests/test_event_spine.py)
- Add restart abort test proving abort succeeds after replay in [`test_execution_manager.py`](tests/test_execution_manager.py)
- Add mutation guard tests for Order and Position in [`test_domain_core.py`](tests/test_domain_core.py)
- Add VWAP accuracy tests in [`test_trading_state.py`](tests/test_trading_state.py)

## v0.38.0 on 7th of April, 2026

- Add nested dataclass hydration to `_coerce` with cached type hints for complex event types in [`event_spine.py`](praxis/infrastructure/event_spine.py)
- Add `execution_params` validation requiring `SingleShotParams` for `SINGLE_SHOT` mode in [`trade_command.py`](praxis/core/domain/trade_command.py)
- Add precomputed `_TYPE_HINTS` dict at module load avoiding `get_type_hints()` per-hydration in [`event_spine.py`](praxis/infrastructure/event_spine.py)
- Add `command_to_order` index to `_AccountRuntime` for O(1) abort order lookup in [`execution_manager.py`](praxis/core/execution_manager.py)
- Add `_request_with_retry` method extracting retry loop from request methods in [`binance_adapter.py`](praxis/infrastructure/binance_adapter.py)
- Add `get_trading_state(account_id)` and `trade_id_for_command(command_id)` public accessors in [`execution_manager.py`](praxis/core/execution_manager.py)
- Refactor `_signed_request` and `_api_key_request` to use `_request_with_retry` callable factory in [`binance_adapter.py`](praxis/infrastructure/binance_adapter.py)
- Refactor `Trading.start()` event grouping to single-pass `defaultdict` accumulation in [`trading.py`](praxis/trading.py)
- Refactor `Trading` reconciliation and WebSocket handlers to use public `ExecutionManager` accessors in [`trading.py`](praxis/trading.py)
- Update WebSocket frame parsing to use `orjson.loads` with UTF-8 encoding in [`binance_ws.py`](praxis/infrastructure/binance_ws.py)
- Remove TD-001, TD-003, TD-005, TD-007, TD-008, TD-010, TD-011, TD-012, TD-016 from [`TechnicalDebt.md`](docs/TechnicalDebt.md)
- Add nested dataclass hydration test in [`test_event_spine.py`](tests/test_event_spine.py)
- Add execution_params validation test in [`test_domain_commands.py`](tests/test_domain_commands.py)

## v0.39.0 on 16th of April, 2026

- Add thread-safety assertion to `enqueue_ws_event` rejecting calls from non-event-loop threads in [`execution_manager.py`](praxis/core/execution_manager.py)
- Add concurrency test proving thread-safety assertion and concurrent fill + command submission in [`test_td014_concurrency.py`](tests/test_td014_concurrency.py)
- Add `Trading.loop` property exposing asyncio event loop after `start()` in [`trading.py`](praxis/trading.py)
- Add per-account outcome routing via `register_outcome_queue()`, `unregister_outcome_queue()`, `route_outcome()` on `Trading` in [`trading.py`](praxis/trading.py)
- Add [`market_data_poller.py`](praxis/market_data_poller.py) with `MarketDataPoller` — per-kline-size polling threads via TDW `get_binance_spot_klines`, runtime `add_kline_size()`/`remove_kline_size()` with reference counting
- Add [`launcher.py`](praxis/launcher.py) with `Launcher` class orchestrating Praxis + Nexus + Limen in one process: asyncio loop thread, Trading, MarketDataPoller, per-account Nexus Manager threads, SIGINT/SIGTERM graceful shutdown
- Add optional `strategy_id` passthrough from `submit_command` to `Position` via `TradingState.trade_strategy_ids` mapping
- Add `polars>=1.0` and `quickstart_etl` (TDW control plane) as runtime dependencies
- Add `vaquum_limen` and `vaquum-nexus` as runtime dependencies (git install)
- Remove resolved TD-002, TD-004, TD-013, TD-014 from [`TechnicalDebt.md`](docs/TechnicalDebt.md)
- Update TD-016 to reflect resolved subitems (event loop, outcome routing, market data poller, launcher)
- Add TD-017 for runtime kline_size registration
- Add integration tests: launcher lifecycle, command submission, outcome routing, full cycle with strategy_id in [`test_launcher.py`](tests/test_launcher.py)
- Add 23 tests across new modules (723 total)

## v0.40.0 on 18th of April, 2026

- Add frozen `HealthSnapshot` dataclass with finite/non-negative invariants, ratio bounds, and `consecutive_failures` int check in [`health_snapshot.py`](praxis/core/domain/health_snapshot.py)
- Add `HealthTracker` with rolling latency + success/failure samples, thread-safe `record_request`, and p99/failure-rate composition in [`health_tracker.py`](praxis/core/health_tracker.py)
- Wire per-account `HealthTracker` into `BinanceAdapter`: `_request_with_retry` records latency and outcome once per call (retries internal); add `rate_limit_utilization`/`clock_drift_ms` properties; add `sync_clock_drift()` against `/api/v3/time`; add `get_health_snapshot(account_id)` that composes tracker + venue-wide metrics in [`binance_adapter.py`](praxis/infrastructure/binance_adapter.py)
- Add `get_health_snapshot(account_id) -> HealthSnapshot` to `VenueAdapter` Protocol in [`venue_adapter.py`](praxis/infrastructure/venue_adapter.py)
- Add `Trading.get_health_snapshot(account_id)` async method (start-required) so Manager can call via `asyncio.run_coroutine_threadsafe(trading.get_health_snapshot(...), trading.loop)` in [`trading.py`](praxis/trading.py)
- Add 46 tests across `test_health_snapshot.py`, `test_health_tracker.py`, `test_binance_adapter.py` (TestHealthSignals), and `test_trading.py`

## v0.41.0 on 20th of April, 2026

- BREAKING: Rewrite the launcher entrypoint for multi-account from a directory of manifests. `MANIFESTS_DIR` env var points at a directory of per-account manifest YAMLs; launcher enumerates them, pre-loads each to extract `account_id` and `allocated_capital`, looks up per-account Binance creds from `BINANCE_API_KEY_<ACCOUNT_ID>` / `BINANCE_API_SECRET_<ACCOUNT_ID>` (suffix normalized: non-alphanumeric → `_`, uppercased), builds one `TradingConfig` with all account credentials and one `InstanceConfig` per manifest
- BREAKING: Remove `allocated_capital` from [`praxis.launcher.InstanceConfig`](praxis/launcher.py) — sourced from the loaded Nexus `Manifest` now (requires `vaquum-nexus >= 0.28.0`)
- BREAKING: Drop `allocated_capital` and `account_id` args from the `StartupSequencer` call in `_run_nexus_instance`; drop the `allocated_capital` arg from the `load_manifest` call in `_collect_kline_intervals` (both match the new Nexus API)
- BREAKING: Change env-var contract — drop `ACCOUNT_ID`, `ALLOCATED_CAPITAL`, `MANIFEST_PATH`, `API_KEY`, `API_SECRET`, `STATE_DIR`, `STRATEGY_STATE_PATH`; add `MANIFESTS_DIR`, `STATE_BASE`, `STRATEGY_STATE_BASE`, per-account `BINANCE_API_KEY_<ACCOUNT_ID>` / `BINANCE_API_SECRET_<ACCOUNT_ID>`
- BREAKING: Bump minimum Python from 3.10 to 3.12. `pyproject.toml` (`requires-python`, ruff `target-version`, mypy `python_version`), all three CI workflows (`pr_checks_tests.yml`, `pr_checks_mypy.yml`, `pr_checks_codeql.yml`), and documentation (`Setup-And-Verification.md`) updated. Required by `binancial` which uses `datetime.UTC` (3.11+) and PEP 695 `type` statements (3.12+)
- Add [`Dockerfile`](Dockerfile) (Python 3.12-slim, installs `git` for git-sourced deps, non-root `praxis` user, entrypoint `python -m praxis.launcher`) and [`.dockerignore`](.dockerignore)
- Add [`render.yaml`](render.yaml) blueprint — single Render Web service, `region: frankfurt`, `plan: starter`, `numInstances: 1`, `autoDeploy: false`, `healthCheckPath: /healthz`, 10 GB persistent disk mounted at `/var/lib/praxis`. Per-account secrets declared `sync: false`
- Add `/healthz` endpoint on the launcher's asyncio loop via `aiohttp`: returns 200 when `Trading.started`, the loop thread is alive, `_stop_event` is unset, and every Nexus thread is alive; 503 with a `failures:` list otherwise. Stopped first in `_shutdown` so Render sees unhealthy immediately on `SIGTERM`. `Launcher.__init__` gains optional `healthz_port: int | None = None`
- Resolve `/healthz` bind port from `PORT` (Render-injected), then `HEALTHZ_PORT`, then default `8080`. Guard signal-handler registration on `threading.main_thread()` so tests can drive `launch()` from a worker thread
- Route launcher `main()` logging through [`observability.configure_logging`](praxis/infrastructure/observability.py) (structlog + orjson JSON to stdout) when `LOG_FORMAT=json` (default); `LOG_FORMAT=text` falls back to stdlib `basicConfig` for local dev. `bind_context(epoch_id=...)` before `Launcher.launch()` so every record carries `epoch_id`
- Add optional `db_path: Path | None = None` to `Launcher`; when set, opens an `aiosqlite` connection on its own loop and builds the `EventSpine` internally (mutually exclusive with the caller-built `event_spine` path). Connection closed during shutdown
- Migrate [`MarketDataPoller`](praxis/market_data_poller.py) off `tdw_control_plane.query.get_binance_spot_klines` to `binancial.compute.get_spot_klines` (Binancial commit `634d5bd`). Lazily build `binance.client.Client(None, None)` for public klines (no credentials needed); compute `start_date` as `now - n_rows * kline_size` seconds; convert the returned pandas DataFrame to polars. Swap `pyproject.toml` dep `quickstart_etl @ git+.../tdw-control-plane` → `binancial @ git+.../Binancial`
- Lift delayed `import polars as pl` to the top of [`praxis/launcher.py`](praxis/launcher.py)
- Add [`docs/Deployment-Render.md`](docs/Deployment-Render.md) with full Render deployment runbook; rewrite [`docs/Launcher.md`](docs/Launcher.md) for the multi-account env-driven entrypoint + `/healthz` + JSON logging; add a "Two Different Health Concepts" section to [`docs/Health.md`](docs/Health.md) distinguishing `HealthSnapshot` from `/healthz`; list the new deployment guide in [`docs/README.md`](docs/README.md)
- Add [`tests/test_launcher_healthz.py`](tests/test_launcher_healthz.py) (healthy-path + shutdown-path) and [`tests/test_launcher_json_logging.py`](tests/test_launcher_json_logging.py) (JSON parseable, bound-context field, text-fallback). Update [`tests/test_launcher.py`](tests/test_launcher.py) `_make_manifest_yaml` to emit the required `account_id:` + `allocated_capital:` fields and drop `allocated_capital=` from `InstanceConfig(...)` call sites
- Add 5 tests across `test_launcher_healthz.py` and `test_launcher_json_logging.py` (776 total)

## v0.42.0 on 22nd of April, 2026

- Add `_build_nexus_instance_config(praxis_inst, manifest)` in [`launcher.py`](praxis/launcher.py) — builds the per-account Nexus runtime `InstanceConfig` (account_id, `venue='binance_spot'`, `STPMode.CANCEL_TAKER`, `duplicate_window_ms=1000`, `capital_pct` mirrored from manifest) consumed by the validator pipeline and `translate_to_trade_command`. Carries MMVP-conservative defaults; Stage-3 price thresholds and per-process rate limits intentionally unset (PT.1.4.1)
- Add `_build_validation_pipeline(nexus_config, capital_controller, *, health/platform/price snapshot providers)` plus three default snapshot factories (`_default_health_snapshot`, `_default_platform_snapshot`, `_default_price_snapshot`). Wires all six validator stages — intake hooks built once via `build_default_intake_hooks` (preserving duplicate-window state across ticks), `RiskStageLimits()` / `PlatformLimitsStageLimits()` / `HealthStagePolicy()` MMVP-lenient (all thresholds unset), `PriceStageLimits` derived via `build_price_stage_limits_from_config`. Snapshot providers read on every `validate()` call so PT.5 / PT.3 can plug in richer state without rebuilding (PT.1.4.2)
- Add `_build_validation_context(action, strategy_id, ...)` plus `_build_enter_context` / `_build_exit_context` private helpers in [`launcher.py`](praxis/launcher.py) — maps a strategy `Action` onto a `ValidationRequestContext`. ENTER derives `order_notional` from `action.size * (action.reference_price or fallback_price_provider())` and returns `None` (logged) when no price is available; `estimated_fees = order_notional * fee_rate` (Binance taker default 0.001); `strategy_budget` from `CapitalController.compute_strategy_budget`. EXIT pulls notional and symbol from `state.positions[action.trade_id]` and returns `None` when the trade is missing. MODIFY logs a TD warning and returns `None`; ABORT returns `None` since `submit_actions` bypasses the validator for it. New module constants `_DEFAULT_FEE_RATE = 0.001`, `_DEFAULT_SYMBOL = 'BTCUSDT'` (PT.1.4.3)
- Add `_extract_kline_sizes(manifest)` and `_last_close_from_poller(poller, kline_sizes)` helpers in [`launcher.py`](praxis/launcher.py); rewire `_run_nexus_instance` so each account builds the Nexus `InstanceConfig`, `CapitalController`, six-stage `ValidationPipeline`, capital-pct-by-strategy map, fallback-price provider, `build_context` closure, and a `submitter(actions, strategy_id)` closure that calls `submit_actions(...)` with `now=lambda: datetime.now(UTC)`. Both `PredictLoop` and `TimerLoop` receive `action_submit=submitter`. Switches to the new public `sequencer.manifest` / `sequencer.instance_state` accessors so `ShutdownSequencer` no longer reaches into private attributes (PT.1.4.4)
- Add `_build_strategy_context(state, manifest, strategy_id)` in [`launcher.py`](praxis/launcher.py) — replaces the hardcoded `(positions=(), capital_available=0, operational_mode=ACTIVE)` stub. Returns a halted, zero-capital context when state or manifest is unavailable (HALTED rather than ACTIVE so strategies cannot act on a stub view as if all-clear); otherwise computes `capital_available = max(manifest.capital_pool * spec.capital_pct / 100 − state.capital.per_strategy_deployed[sid], 0)`, filters `positions` to the strategy_id, and resolves `operational_mode` from `state.strategy_modes[sid].state.mode` (per-strategy override) or `state.mode.mode` (instance-level fallback). The runtime closure inside `_run_nexus_instance` reads `sequencer.instance_state` and `sequencer.manifest` on every call so reservations and operational-mode transitions show up between ticks (PT.2.2)
- Wire `OutcomeLoop` into `_run_nexus_instance`. Builds a per-account `command_strategy_ids: dict[str, str]` registry; submitter captures `submit_actions(...)` results and records `command_id → strategy_id` on each `SubmissionStatus.SUBMITTED`. The registry key is the Praxis-assigned id returned by `PraxisOutbound.send_command` — that is also the id carried on the inbound `TradeOutcome.command_id`, so `resolve_strategy_id` is a simple dict lookup. OutcomeLoop instantiated with the same `runner`, `praxis_inbound`, `state`, `context_provider`, and `submitter`; started alongside `predict_loop`. `ShutdownSequencer` now receives `outcome_loop=outcome_loop` so the upstream PT.3.3 stop hook actually fires (PT.3.2)
- Require `vaquum-nexus >= 0.29.0` at runtime (`StartupSequencer.instance_state` / `manifest` accessors, `nexus.core.outcome_loop.OutcomeLoop`, `nexus.strategy.action_submit.submit_actions`)
- Add 7 tests in [`test_launcher_nexus_instance_config.py`](tests/test_launcher_nexus_instance_config.py) covering account_id propagation, default venue / STPMode / duplicate-window, Stage-3 thresholds left None, capital_pct mirrored from manifest, empty-strategies case (PT.1.4.1)
- Add 9 tests in [`test_launcher_validation_pipeline.py`](tests/test_launcher_validation_pipeline.py) covering all six stages present, ENTER allow path, capital denial when reservation > pool, intake duplicate-command-id denial, price snapshot provider invoked per call, price denial when spread exceeds limit, MMVP defaults skip price checks, health provider invoked per call, decision-type sanity (PT.1.4.2)
- Add 10 tests in [`test_launcher_validation_context.py`](tests/test_launcher_validation_context.py) covering ENTER ref-price path, ENTER fallback, ENTER no-price → None, fee math, strategy_budget formula, command-id auto-generation, EXIT from position (notional + symbol + side), EXIT missing trade → None, MODIFY → None, ABORT → None (PT.1.4.3)
- Add 3 tests in [`test_launcher_submitter_e2e.py`](tests/test_launcher_submitter_e2e.py) covering ENTER → validator allow → translate → `praxis_outbound.send_command` called once with the expected `TradeCommand`, EXIT for unknown trade_id dropped (no `send_command`), ABORT bypasses validator and triggers `send_abort` with `reason='runtime_strategy_abort'` (PT.1.4.4)
- Add 9 tests in [`test_launcher_strategy_context.py`](tests/test_launcher_strategy_context.py) covering state-None, manifest-None, unknown-strategy, full-budget, deployed-subtraction, over-deployed clamp, position filtering, per-strategy mode override, instance-mode fallback (PT.2.2); plus 2 tests in `TestContextReflectsReservations` covering capital_available drops by reservation notional + fees, and per-strategy isolation (PT.2.3)
- Add 4 tests in [`test_launcher_outcome_flow_e2e.py`](tests/test_launcher_outcome_flow_e2e.py) covering registry populated on SUBMITTED, outcome dispatched via registry, orphan outcome silently skipped, returned-actions feedback loop (PT.3.4)
- Add 50 tests across new files (826 total)
- Split `Launcher._run_nexus_instance` into a 39-line orchestration step (`build runtime → wait → ShutdownSequencer.shutdown`) and a new private `Launcher._build_nexus_runtime(inst, outcome_queue) -> _NexusRuntime` method that wires every per-account component (StateStore, PraxisOutbound, StartupSequencer, NexusInstanceConfig, CapitalController, ValidationPipeline, build_context / submitter / context_provider closures, PredictLoop, TimerLoop, OutcomeLoop) and starts the loops. Adds a private `_NexusRuntime` dataclass to group the wired components for handoff to the lifecycle step

## v0.43.0 on 23rd of April, 2026

- Add [`Trading.set_on_trade_outcome(cb)`](praxis/trading.py) — installs the `on_trade_outcome` callback after `Trading()` construction, closing the chicken-and-egg gap where `TradingConfig.on_trade_outcome` cannot reference the not-yet-built `Trading` instance. Always wraps the user callback in an `async` adapter that `await`s the result when `inspect.isawaitable(...)`, so coroutine functions, plain sync callables, `functools.partial` around coroutine functions, `AsyncMock`, and async-`__call__` callable objects are all handled uniformly. Raises `RuntimeError` if called once `Trading.start()` has begun — the guard keys on `self._started or self._loop is not None`, so mid-startup swaps (after `start()` sets `self._loop` but before `self._started`) are also rejected (PT.4.1)
- Add [`ExecutionManager.set_on_trade_outcome(cb)`](praxis/core/execution_manager.py) — the underlying setter that `Trading.set_on_trade_outcome` forwards to, storing the callback that `ExecutionManager` awaits when producing outcomes. The pre-`start()` guard lives on `Trading.set_on_trade_outcome` (the only public entry point); direct `ExecutionManager` calls reserved for tests stay unrestricted (PT.4.1)
- Wire [`launcher.py`](praxis/launcher.py) `_start_trading` to install the outcome callback immediately after `Trading()` construction and before `await trading.start()`, and pre-register the per-account `queue.Queue[TradeOutcome]` for every instance in the same window. Without the pre-registration, `Trading.start()` reconciliation could enqueue WS events that produce terminal outcomes before `_start_nexus_instances` got around to calling `register_outcome_queue`, and those outcomes would be routed to no-such-queue and dropped. The same `queue.Queue` objects are reused when each Nexus thread builds its `PraxisInbound`. When `TradingConfig.on_trade_outcome` is unset (the default), the launcher registers `Trading.route_outcome` so per-account `TradeOutcome`s land on the queues consumed by the `OutcomeLoop` from Praxis #73. When `TradingConfig.on_trade_outcome` is set by the consumer, the launcher composes an async wrapper that calls `route_outcome` first and then awaits the user callback, so external telemetry / sink integrations are preserved alongside the runtime queue routing (PT.4.2)
- Add 7 tests in [`test_trading.py`](tests/test_trading.py) covering: sync callback wrapped + invoked, async callback wrapped + invoked, `functools.partial` around an async callable wrapped + awaited (the always-wrap path the previous `iscoroutinefunction` branch would have misclassified), `None` clears, `RuntimeError` after `Trading.start()` completes, `RuntimeError` mid-`start()` (driven by patching `event_spine.read` to call the setter during replay), and `register_outcome_queue` + `set_on_trade_outcome(route_outcome)` end-to-end with the registered queue receiving the routed `TradeOutcome` (PT.4.3)
- 833 tests passing (up from 826). Bumps `vaquum-praxis` 0.42.0 → 0.43.0

## v0.44.0 on 23rd of April, 2026

- Add `_build_praxis_outbound(trading, loop)` module-level helper in [`launcher.py`](praxis/launcher.py) that wires every outbound callable Nexus needs against the Praxis `Trading` singleton, including `submit_abort_fn` and `get_health_snapshot_fn` which the #72 / #73 launcher silently omitted. Without the wiring, `PraxisOutbound.send_abort` raised `RuntimeError('submit_abort_fn not configured')` at first use (regressing `ShutdownSequencer` abort escalation and the `submit_actions` ABORT path) and `get_health_snapshot` was unreachable. `Trading.submit_abort` is sync; the helper wraps it in an async adapter that matches the kwargs-shape `PraxisOutbound.send_abort` passes via `run_coroutine_threadsafe`, reconstructing a `TradeAbort` on the Praxis-loop side (PT.5.1)
- Add `_build_health_loop(praxis_outbound, state, account_id, interval_seconds=5.0)` module-level helper in [`launcher.py`](praxis/launcher.py) that builds the per-account `HealthLoop`. Each tick pulls a `HealthSnapshot` via `praxis_outbound.get_health_snapshot(account_id)` (crosses the thread/loop boundary into Praxis via `run_coroutine_threadsafe`), evaluates it through `HealthEvaluator(HealthThresholds())` with MMVP defaults (200/500/1000 ms latency warn/breach/halt, 3/5/10 consecutive failures, 10/20/40% failure rate, 70/85/90% rate-limit headroom, 500 ms clock drift), and updates `state.mode` on transition. The Praxis `HealthSnapshot` dataclass is field-compatible with the Nexus `HealthSnapshot` that `HealthEvaluator.evaluate` reads (same `latency_p99_ms` / `consecutive_failures` / `failure_rate` / `rate_limit_headroom` / `clock_drift_ms` attribute names), so the provider returns Praxis's type and the evaluator duck-types it without conversion (PT.5.2)
- Add `health_loop: HealthLoop` field to `_NexusRuntime` in [`launcher.py`](praxis/launcher.py); `_build_nexus_runtime` calls `health_loop.start()` right after `outcome_loop.start()` so per-account health tracking begins as soon as startup completes (PT.5.2)
- Add new constant `_DEFAULT_HEALTH_INTERVAL_SECONDS = 5.0` in [`launcher.py`](praxis/launcher.py) matching the RFC-4001 §Health cadence
- Wire `runtime.health_loop.stop()` inside `Launcher._run_nexus_instance` immediately after `self._stop_event.wait()` returns and before building `ShutdownSequencer`. Mirrors the shutdown discipline of `OutcomeLoop` (which `ShutdownSequencer` stops via its PT.3.3 hook) without extending the sequencer signature — `HealthLoop` only mutates `state.mode` and doesn't share any external resource with the shutdown drain, so launcher-side stop is sufficient. `HealthLoop.stop()` is idempotent (PT.5.3)
- Note on policy alignment: the validator `HealthStagePolicy` (Decimal-typed, driven by `_build_validation_pipeline`) and `HealthEvaluator`'s `HealthThresholds` (float-typed, driven by `_build_health_loop`) are separate policy objects today — the two types have different field names and shapes, so they cannot be shared. Aligning them onto a single policy object is a post-MMVP concern tracked in Praxis issue #75
- Add 4 tests in [`test_launcher_health_loop.py`](tests/test_launcher_health_loop.py) covering: the build helper returns a HealthLoop instance, a degraded snapshot (latency_p99_ms = 2000 ms exceeding `HealthThresholds.latency_halt_ms = 1000 ms`) flips `state.mode.mode` to `HALTED` with `trigger == 'health'` after `tick_once()`, healthy snapshot leaves `state.mode` untouched, and `start()`/`stop()` idempotency with a bounded-poll assertion that the worker thread actually ran (PT.5.4)
- Add 4 tests in [`test_launcher_outbound_wiring.py`](tests/test_launcher_outbound_wiring.py) covering: sanity check that the build helper returns a `PraxisOutbound`, end-to-end `send_abort` round-trip on a real loop thread reaching `Trading.submit_abort` with the reconstructed `TradeAbort`, `get_health_snapshot` round-trip reaching `Trading.get_health_snapshot`, and a documentation-style test showing a bare `PraxisOutbound` raises `RuntimeError('submit_abort_fn not configured')` today (pins the regression PT.5.1 fixes) (PT.5.1)
- 841 tests passing (up from 833). Bumps `vaquum-praxis` 0.43.0 → 0.44.0

## v0.45.0 on 27th of April, 2026

- Bump `vaquum-nexus` pin from `3bda07e7` to `f3fd91f1` (Nexus v0.32.0 — Vaquum/Nexus#45 merged), aligning Praxis with the Nexus paper-trade-readiness PT-FIX series and the new `OrderContext.is_entry` field
- Add PT-FIX-1 lazy kline-size registration from wired sensors in [`launcher.py`](praxis/launcher.py) — kline sizes are now read from each `WiredSensor.limen_manifest` after `sequencer.start()` trains the manifest, so the poller is no longer empty at boot and `signal_producer.produce_signal` no longer raises `ValueError("market_data is empty for sensor X")` on every tick
- Add PT-FIX-2 `ShutdownSequencer.config` wiring in [`launcher.py`](praxis/launcher.py) so `on_shutdown` actions execute through `translate_to_trade_command` instead of failing with `RuntimeError('config not configured')`
- Add PT-FIX-3 testnet routing for `MarketDataPoller` in [`launcher.py`](praxis/launcher.py) when `BINANCE_TESTNET=true`
- Add PT-FIX-4 Limen pin alignment to `v2.4.3` matching Nexus
- Add PT-FIX-6 outcome translation seam in [`outcome_translator.py`](praxis/outcome_translator.py) — Praxis `TradeOutcome` is mapped to the Nexus shape on the per-account queue boundary so `OutcomeLoop` consumes the right type
- Add PT-FIX-7 outbound `execution_params → SingleShotParams` wrapping via [`launcher.py`](praxis/launcher.py)`_build_praxis_outbound` and [`command_translator.py`](praxis/command_translator.py)`build_single_shot_params` so `submit_command` reaches the Praxis venue with the right param object
- Add PT-FIX-8 per-account `OutcomeProcessor` wiring in [`launcher.py`](praxis/launcher.py) (`process_outcome` closure built from the per-account `CapitalController` + `InstanceState` + `StateStore`)
- Add PT-FIX-10 lock around `TradingState.positions` reads in [`trading_state.py`](praxis/trading_state.py) — pairs with the writer-side lock to prevent partial-snapshot reads during concurrent fill ingestion
- Add PT-FIX-11 `BINANCE_TESTNET` documentation in `docs/Launcher.md` optional-env table
- Add PT-FIX-12 fixed pins for `vaquum-nexus` and `binancial` in `pyproject.toml` (no more floating `main` refs)
- Add PT-FIX-13 `BinanceAdapter` post-close session re-creation refusal in [`binance_adapter.py`](praxis/infrastructure/binance_adapter.py) — once `close()` runs, subsequent `_session_factory()` calls raise instead of silently re-opening a session
- Add PT-FIX-14 sync `Trading.get_health_snapshot_sync(account_id)` API in [`trading.py`](praxis/trading.py) (consumed by `_build_health_loop` in [`launcher.py`](praxis/launcher.py)) so the Nexus HealthLoop reads snapshots without crossing the asyncio boundary on every tick
- Add PT-FIX-16 `on_startup` action drain in [`launcher.py`](praxis/launcher.py) — actions returned from `Strategy.on_startup` now flow through the same `submit_actions` pipeline as runtime actions
- Add PT-FIX-19 `strategies_base_path` prepend to `sys.path` BEFORE `_wire_sensors` in [`launcher.py`](praxis/launcher.py) so user strategy packages resolve during sensor wiring
- Add PT-FIX-20 ENTER `Position` pre-population in [`launcher.py`](praxis/launcher.py) — `_ensure_entry_position` registers the `Position(trade_id=command_id, …)` BEFORE the first FILL outcome lands, so `OutcomeProcessor._grow_position` finds the position record by `forced_trade_id` instead of raising "entry fill for missing position"
- Add PT-FIX-21 venue-adapter close on `Trading.stop()` in [`trading.py`](praxis/trading.py) so the HTTP session is released
- Add PT-FIX-22 `/healthz` listener kept up across shutdown in [`launcher.py`](praxis/launcher.py) — Render now gets a clean 503 with `failures:` payload on `SIGTERM` instead of connection-refused
- Add PT-FIX-23 hold `_positions_lock` through the field-mutation branches in [`trading_state.py`](praxis/core/trading_state.py) (`_update_position_on_fill` insert, accumulate, and reduce paths; plus `_on_trade_closed` pop)
- Add PT-FIX-24 set `_stop_event` on per-instance build failure in [`launcher.py`](praxis/launcher.py) so `launch()` unwinds cleanly when `_build_nexus_runtime` raises
- Add PT-FIX-28 shared `positions_lock` in [`launcher.py`](praxis/launcher.py) — `state.positions` iteration in the `_NexusRuntime` and the terminal-cleanup `del` in `process_outcome` now hold the same lock so the dict doesn't mutate mid-iteration
- Add PT-FIX-29 atomic `command_strategy_ids` + `command_contexts` writes under shared `command_registry_lock` in [`launcher.py`](praxis/launcher.py)
- Add PT-FIX-30 boot-time orphan `CommandAccepted` reconciliation in [`execution_manager.py`](praxis/core/execution_manager.py) (`reconcile_orphan_commands`) so stranded Nexus reservations get released after a crash
- Add PT-FIX-31 `OutcomeProcessor` threading through `_NexusRuntime` into `ShutdownSequencer` in [`launcher.py`](praxis/launcher.py) so shutdown EXIT FILLs decrement `state.positions` instead of being silently dropped
- Add PT-FIX-35 `CapitalController.reconcile_at_boot()` call in [`launcher.py`](praxis/launcher.py) `_build_nexus_runtime` so stranded `in_flight_order_notional` / `working_order_notional` / `reservation_notional` from a crashed prior boot are reset
- Add PT-FIX-39 bounded `OrderedDict` LRU for `OutcomeTranslator`'s terminal-dedup table in [`outcome_translator.py`](praxis/outcome_translator.py) — replaces an unbounded `set` with a default cap of 10000 + FIFO eviction
- Add PT-FIX-41 pass `state.positions.values()` to `reconcile_at_boot` in [`launcher.py`](praxis/launcher.py) `_build_nexus_runtime` so `per_strategy_deployed` is rebuilt from live positions (without it, the persisted per-strategy attribution still includes pre-crash reservation/in-flight/working amounts and the next `check_and_reserve` permanently denies all new ENTERs)
- Add PT-FIX-44 `process_outcome` threading through `_NexusRuntime` to `ShutdownSequencer.non_pending_outcome_handler` in [`launcher.py`](praxis/launcher.py) so pre-shutdown outcomes drained by `_poll_until_terminal` are routed through the same outcome handler the OutcomeLoop would have used
- Thread `is_entry` through `_build_order_context` in [`launcher.py`](praxis/launcher.py) — `is_entry=action.action_type == ActionType.ENTER` matches the new required `OrderContext.is_entry` field in Nexus 0.32.0. Decouples intent from venue side so short-position EXITs (BUY-to-cover) are no longer mis-routed through `OutcomeProcessor`'s entry path
- Add TD-021..024 (round-6/7 audit deferred edge cases) to [`docs/TechnicalDebt.md`](docs/TechnicalDebt.md)
- 925 tests passing (up from 841). Bumps `vaquum-praxis` 0.44.0 → 0.45.0

## v0.46.0 on 29th of April, 2026

- Add [`ExecutionManager._emit_ws_outcome(runtime, event)`](praxis/core/execution_manager.py) invoked from `_account_loop` after every successful `trading_state.apply()` — for `FillReceived` / `OrderCanceled` / `OrderRejected` / `OrderExpired` events, derives cumulative state from the now-updated `Order` projection (filled_qty, cumulative_notional, status), maps `OrderStatus → TradeStatus`, and forwards to `_build_outcome` so spine persistence + `_on_trade_outcome` callback fire on the WS-driven path. Pre-fix `_build_outcome` was only invoked from `_process_command`, so a SINGLE_SHOT LIMIT order returning no `immediate_fills` exited at PENDING and any subsequent venue WS fill was invisible to Nexus — capital stayed in `working_order_notional`, the launcher's per-account `process_outcome` closure never fired, and any operator LIMIT strategy silently lost every fill (BLOCKER-D)
- Skip the `_emit_ws_outcome` emission when the `command_id` is already in `_terminal_commands` to dedupe against `_process_command`'s immediate-fill emission for MARKET orders that fill inside `submit_order.immediate_fills`
- Add zombie cleanup in [`TradingState._update_position_on_fill`](praxis/core/trading_state.py) opposite-side branch — when `new_qty == _ZERO`, `del self.positions[key]` and pop `self.trade_strategy_ids[event.trade_id]`. Pre-fix the position stayed as a qty=0 zombie because `_on_trade_closed` (the only deletion path) only fires on `TradeClosed` events emitted from `_build_outcome`. The zombie rode into the next snapshot via `pull_positions` and the spine, then the next Nexus boot's `_reconcile_capital` imported it and `reconcile_at_boot(positions=state.positions.values())` rebuilt `per_strategy_deployed` from the zombie → attribution mismatch denial → every ENTER for the rest of the boot rejected. Closes the Praxis-side ingress for the failure mode tracked as BLOCKER-B in Nexus (BLOCKER-E)
- Wire [`StateStore.append_mutation(state)`](praxis/launcher.py) call into the launcher's `_build_nexus_runtime.process_outcome` closure — fires after each successful state-mutating `OutcomeProcessor.process` where `position_updated` is true, so a SIGKILL/OOM/container restart between checkpoints recovers to the most recent terminal outcome rather than rolling back to the last clean shutdown. Persistence failures are caught and logged at exception level so an outage never aborts the outcome flow. Cadence rationale: per-terminal-outcome was chosen over a periodic snapshot thread because outcomes are the only sites that mutate `position_notional` / `per_strategy_deployed` and the runtime's state-mutating events are sparse enough at MMVP order rates that I/O cost is negligible (BLOCKER-B.1, B.2)
- Update [`tests/test_launcher.py`](tests/test_launcher.py)`test_full_cycle_submit_fill_outcome_shutdown` to assert the corrected end state — WS fill produces FILLED `TradeOutcomeProduced` on the spine and `TradeClosed` deletes the position. Pre-fix the test asserted the qty=0 zombie behavior as a passing case
- Add 6 new tests in `TestEmitWsOutcome` (partial fill emits PARTIAL, full fill emits FILLED terminal, cancel-after-partial emits both PARTIAL+CANCELED with correct filled_qty, EXPIRED branch emits terminal `EXPIRED` outcome with `reason=None`, REJECTED branch emits terminal `REJECTED` outcome with `reason=event.reason`, terminal-command WS echo does not double-emit), 5 new tests in `test_trading_state.py` (position removed when WS exit drives qty to zero, trade_strategy_id removed at the same time, partial close regression, overclose deletion path, snapshot_positions excludes WS-closed position), and 1 new smoke test in [`test_launcher_persistence_wiring.py`](tests/test_launcher_persistence_wiring.py) (asserts `state_store.append_mutation` is called from `_build_nexus_runtime`). Total Praxis tests: 937
- Note: `vaquum-nexus` pin remains at `f3fd91f1` (Nexus v0.32.0 / Vaquum/Nexus#45 merge) for now. A follow-up commit on this branch will bump the pin to the post-merge SHA of Vaquum/Nexus#47 (the Nexus v0.33.0 PR carrying BLOCKER-A / B.3-4 / C; tracked in issue Vaquum/Nexus#46) once that PR lands. Until then Praxis tests run against the editable Nexus install in the local venv, which already carries the BLOCKER-A / B.3/4 / C work
- Tighten the `append_mutation` trigger in [`launcher.py`](praxis/launcher.py)`process_outcome` from `position_updated or capital_updated` to `position_updated` only — ACK outcomes set `capital_updated=True` but mutate only `working_order_notional` / `in_flight_order_notional` book-keeping that `reconcile_at_boot` rebuilds on next boot, so persisting a snapshot per ACK is wasted I/O. Position-level state IS the unique-to-mid-run-persistence concern (greybeard pre-PR review)
- Replace fall-through `else: status = TradeStatus.REJECTED` in [`_emit_ws_outcome`](praxis/core/execution_manager.py) with explicit `elif isinstance(event, OrderRejected)` plus a `RuntimeError` guard on the now-unreachable else; a future event subclass added to the outer `isinstance` filter without updating the chain now fails loudly instead of silently routing through the REJECTED branch and exploding on missing `reason` (greybeard pre-PR review)
- Add [`docs/TechnicalDebt.md`](docs/TechnicalDebt.md) entry TD-028 — `_on_trade_closed` WARNING fires on the WS-driven LIMIT EXIT happy path because the BLOCKER-E zombie cleanup deleted the position before `TradeClosed` reaches the handler. Operational noise; both deletion paths are safe (PR #80 review)
- In [`ExecutionManager.replay_events`](praxis/core/execution_manager.py), reconstruct each non-terminal `TradeCommand` from its `OrderSubmitIntent` event and write it to `self._commands[command_id]` so post-restart WS fills on resting LIMIT orders reach `_emit_ws_outcome` → `_on_trade_outcome` rather than being silently dropped at the `cmd is None` early-return. Also pop `_commands[command_id]` when a `TradeOutcomeProduced` terminal is encountered during replay (memory bound + dedup against the post-restart WS echo path). `MakerPreference.NO_PREFERENCE` / `STPMode.NONE` / `ExecutionMode.SINGLE_SHOT` defaults are used for the fields not on `OrderSubmitIntent` — these fields are not read by `_emit_ws_outcome`'s downstream chain (Vaquum/Praxis#79 MAJOR-F, Copilot PR #80 review)
- In [`ExecutionManager._emit_ws_outcome`](praxis/core/execution_manager.py), clamp the emitted `filled_qty` to `cmd.qty` before calling `_build_outcome` and log a WARNING when clamping fires. Pre-fix `order.filled_qty` could exceed `cmd.qty` due to duplicate / out-of-order venue fills or venue rounding past target, tripping `TradeOutcome.__post_init__`'s `filled_qty <= target_qty` invariant — the resulting raise was caught + logged by `_account_loop` and the outcome was dropped, so Nexus never saw the fill (Copilot PR #80 review)
- Downgrade `TradingState._on_trade_closed` `'no position for TradeClosed'` log from WARNING to DEBUG — fires on the WS-driven LIMIT EXIT happy path because the BLOCKER-E zombie cleanup deleted the position before `TradeClosed` reaches the handler. Both deletion paths are safe; the WARN level was misleading operators (closes TD-028 in code rather than as deferred TD) (Copilot PR #80 review)

## v0.47.0 on 30th of April, 2026

- Add `command_strategy_ids` early-write in [`_build_nexus_runtime`](praxis/launcher.py)'s submitter — registers the strategy_id at the TOP of the for-loop body (before `capital_controller.send_order` / `_ensure_entry_position` / `_build_order_context`) so a fast venue ACK arriving during the post-`send_command` processing window resolves correctly. Pre-fix the registry write happened AFTER all those calls; OutcomeLoop popped a fast ACK, called `resolve_strategy_id`, got None, dropped the outcome silently. `order_ack` never ran → order stayed IN_FLIGHT → subsequent FILL → INVARIANT_BREACH → fill silently dropped on capital side, position not grown, capital permanently stuck in `in_flight_order_notional` (MAJOR-P)
- Pass `positions_lock=runtime.positions_lock` to [`OutcomeProcessor`](praxis/launcher.py) construction. Pre-fix the lock was created and threaded into readers (`_build_strategy_context`) and entry-placeholder writers (`_ensure_entry_position`) but never into `OutcomeProcessor` — the writer mutated `state.positions` unguarded against PredictLoop's lock-protected iteration → silent strategy-tick drops via `RuntimeError: dictionary changed size during iteration`. Updated `_build_strategy_context` docstring (TD-W) to reflect actual post-MAJOR-J locking semantics (MAJOR-J + TD-W)
- Change `process_outcome`'s `state_store.append_mutation` gate from `result.success and result.position_updated` to `result.success and (result.position_updated or result.capital_updated)` so ACK / non-fill REJECT / non-fill CANCEL outcomes (which mutate `in_flight_order_notional`, `working_order_notional`, `per_strategy_deployed` but return `position_updated=False`) persist to WAL between checkpoints (MAJOR-M)
- Pass `capital_controller=capital_controller` to `submit_actions` so the rollback path can call `controller.release_reservation(reservation_id)` on translate / send_command failure. Praxis-side wiring for Vaquum/Nexus MAJOR-G
- Pass `positions_lock=runtime.positions_lock` to [`ShutdownSequencer`](praxis/launcher.py) so `_dispatch_shutdown`'s snapshot iteration of `state.positions.values()` honors the same lock that PredictLoop and OutcomeProcessor use. Praxis-side wiring for Vaquum/Nexus MAJOR-S
- Wire `state_store.refresh_rolling_losses` into [`HealthLoop`](praxis/launcher.py) via the new `_build_health_loop` `state_store` parameter so 24h/7d/30d rolling-loss windows decay as old loss events age out. Without this wiring the Nexus-side rolling-loss enforcement (Vaquum/Nexus MAJOR-H) would be over-conservative because the fields would only ever grow
- Pop `command_strategy_ids[outcome.command_id]` under `command_registry_lock` when `capital_controller.send_order` returns failure post-MAJOR-P — the entry was previously left as a zombie, accumulating one per failed `send_order`. Tighten `test_strategy_id_resolvable_during_send_order_concurrent` to assert the writer thread completed without exception and produced 200 entries (Greybeard pre-PR review)
- Add 6 new tests across [`test_launcher_command_registry_lock.py`](tests/test_launcher_command_registry_lock.py) (`TestMajorPRegistryRaceWindow`: strategy_id-set-before-send_order pin + concurrent invariant), [`test_launcher_persistence_wiring.py`](tests/test_launcher_persistence_wiring.py) (AST guard for `capital_updated` in the `append_mutation` gate). Total Praxis tests: 942
- Add [`docs/TechnicalDebt.md`](docs/TechnicalDebt.md) entries TD-029 through TD-035 — defer round-13/14 audit findings that are not paper-trade-fatal (`command_contexts` leak on raise, OutcomeTranslator fee_rate=0 latent, REJECTED branch asymmetry, `_build_partial` divide-by-zero risk, ExecutionManager registries grow without purge, unbounded queues, `_emit_ws_outcome` clamp drops surplus venue fill)

## v0.48.0 on 1st of May, 2026

- Add `cumulative_notional: Decimal` field to [`TradeOutcome`](praxis/core/domain/trade_outcome.py) (default `_ZERO`). Construction-time validators now reject (a) negative `cumulative_notional`, (b) non-zero `cumulative_notional` when `filled_qty == 0`, and (c) zero `cumulative_notional` when `filled_qty > 0`. Carries the venue-side `Order.cumulative_notional` (sum of `qty * price` across fills) verbatim so [`OutcomeTranslator`](praxis/outcome_translator.py) does not have to reverse-derive it from `filled_qty * avg_fill_price`, eliminating a precision-lossy round trip that on multi-partial sequences could flip `delta_notional` negative and silently drop the partial fill at `ExecutionManager._build_outcome` (called from `_process_command` / `_process_abort` / `_emit_ws_outcome`) (FINAL-MAJOR-07)
- Hold `command_registry_lock` across the entire submitter critical section in [`_build_nexus_runtime`](praxis/launcher.py:1494-1543): `command_strategy_ids` write → `capital_controller.send_order` → `_ensure_entry_position` → `_build_order_context` → `command_contexts` write. Pre-fix the registry mutations were under separate lock acquisitions with venue I/O in between; a fast venue ACK or terminal non-fill landing in that window resolved the strategy_id, found `command_contexts.get(...)` was None, and silently dropped the outcome — stranding `_orders[command_id]` and inflating capital aggregates (FINAL-MAJOR-01)
- Pass `positions_lock=positions_lock` to `submit_actions` so the EXIT-action `pending_exit +=` accumulator in `praxis/strategy/action_submit.py` is serialized against PredictLoop's lock-protected position iteration (Praxis-side wiring for Vaquum/Nexus FINAL-MAJOR-03)
- Pass `capital_controller=runtime.capital_controller` to [`ShutdownSequencer`](praxis/launcher.py) so `_final_checkpoint` wraps serializer iteration in `positions_lock + CapitalController.lock_cm()` and freezes capital aggregates during shutdown (Praxis-side wiring for Vaquum/Nexus FINAL-MAJOR-05)
- Attach `state.risk.lock = positions_lock` in [`_build_nexus_runtime`](praxis/launcher.py) so Nexus's `RiskState.lock_cm()` serializes `per_strategy` mutations in `OutcomeProcessor._update_strategy_risk_state` against validator-side `to_risk_check_metrics()` reads (Praxis-side wiring for Vaquum/Nexus FINAL-MAJOR-02)
- Add `hasattr(state.risk, 'lock')` guard before the `state.risk.lock = positions_lock` assignment so the launcher fails loud if the pinned Nexus version drops the transient lock slot, instead of silently no-op'ing the FINAL-MAJOR-02 cross-thread serialization (Greybeard pre-PR review)
- Carry `cumulative_notional` through `ExecutionManager._process_command` (immediate-fill path), `_process_abort` (abort path), `_emit_ws_outcome` (WS-driven path), and `_build_outcome` (shared TradeOutcome construction). The immediate-fill path scales `total_notional = total_notional * cmd.qty / filled_qty` on the overfill clamp so the emitted `cumulative_notional` matches the clamped `filled_qty` (one-shot emission; per-emission consistency wins). The WS path forwards `order.cumulative_notional` verbatim with NO scaling on overfill clamp so `cumulative_notional` stays monotonic across PARTIAL → terminal emission sequences for the same command (multi-emit; monotonicity wins). TD-037 documents the resulting asymmetry between the two paths (FINAL-MAJOR-07)
- Bump `vaquum-nexus` pin from `f4eab11` (PR #49 merge) to `7a634b4` (the squash-merge SHA of Vaquum/Nexus#55 on `main`, which lands paper-trade-readiness round-17). Initial pin during PR review pointed at the unmerged round-1 branch HEAD `31d4fa4`; final pin re-bumped to the post-merge SHA after Nexus #55 merged. The pinned Nexus version exposes `RiskState.lock`, `CapitalController.lock_cm()`, and the `outcome_id`-aware WAL codec required by FINAL-MAJOR-02 / 05 / 07
- Add [`TestFinalMajor01AtomicRegistration`](tests/test_launcher_command_registry_lock.py) (2 tests) pinning the no-torn-observation invariant under contention and the reader-blocks-until-both-registries-populated guarantee. Add [`TestFinalMajor07TranslatorUsesVenueCumulativeNotional`](tests/test_outcome_translator.py) (2 tests) pinning that the translator emits non-negative `delta_notional` on drift-inducing partial sequences and that the per-fill emitted notional sums byte-for-byte to the venue cumulative
- Update [`tests/test_domain_outcome.py`](tests/test_domain_outcome.py), [`tests/test_launcher.py`](tests/test_launcher.py), and [`tests/test_trading.py`](tests/test_trading.py) to populate `cumulative_notional` on every full-fill `TradeOutcome` construction so the new positive-fill invariant validator does not reject existing fixtures
- Add [`docs/TechnicalDebt.md`](docs/TechnicalDebt.md) entries TD-037 (overflow-clamp `cumulative_notional` drift), TD-038 (`command_registry_lock → CapitalController._lock` and `command_registry_lock → positions_lock` lock-order pair from the FINAL-MAJOR-01 atomic critical section), and TD-039 (`TestFinalMajor01AtomicRegistration` exercises a local helper, not the real submitter closure)

## v0.49.0 on 3rd of May, 2026

### Add

- Add `TRADE_MODE` env var to the launcher's `_REQUIRED_ENV_VARS` and new [`_resolve_trade_mode(env)`](praxis/launcher.py) helper mapping `paper` / `live` to the in-code REST + WS URL pair from [`praxis/infrastructure/binance_urls.py`](praxis/infrastructure/binance_urls.py). Drops `VENUE_REST_URL`, `VENUE_WS_URL`, and `BINANCE_TESTNET` from the env contract — the operator has no surface to route the order path to mainnet while believing they are on testnet (round-18 MAJOR-001)
- Add `DuplicateClientOrderIdError` and `OrderSubmitTimeoutError` to [`venue_adapter.py`](praxis/infrastructure/venue_adapter.py); both carry `client_order_id`. Add `idempotent: bool = True` kwarg to [`BinanceAdapter._request_with_retry`](praxis/infrastructure/binance_adapter.py) and `_signed_request`. Add [`_post_order`](praxis/infrastructure/binance_adapter.py) helper that runs `idempotent=False` for order POSTs and translates `TransientError` → `OrderSubmitTimeoutError`, `OrderRejectedError(venue_code=-2010)` → `DuplicateClientOrderIdError`. Add [`_rescue_by_client_order_id`](praxis/core/execution_manager.py) and [`_record_submit_failed`](praxis/core/execution_manager.py) helpers in `ExecutionManager._process_command`: on either rescue-trigger error, query the venue by `client_order_id`; on confirmed live order, append `OrderSubmitted` and continue normal lifecycle; on confirmed-not-found or query failure, emit REJECTED via the shared sink (round-18 MAJOR-002)
- Add `LocalOrderRejectedError(OrderRejectedError)` to [`venue_adapter.py`](praxis/infrastructure/venue_adapter.py) carrying `venue_code=-1013` and the rejection reason. [`BinanceAdapter._validate_order`](praxis/infrastructure/binance_adapter.py) raises this typed error for every filter violation (lot_step / lot_min / lot_max / tick_size / min_notional) instead of plain `ValueError`, so the existing `except VenueError` flow in `ExecutionManager._process_command` synthesizes `OrderSubmitFailed` and a REJECTED `TradeOutcome` (round-18 MAJOR-007)
- Add Class B orphan-reconcile path to [`ExecutionManager.reconcile_orphan_commands`](praxis/core/execution_manager.py): scan for `OrderSubmitIntent` events without `OrderSubmitted` / `OrderSubmitFailed` / terminal `TradeOutcomeProduced` follow-up via a `client_order_id` → `command_id` map built during the same scan; synthesize REJECTED for these as boot-time defense-in-depth (round-18 MAJOR-007 M07.2)
- Add `OutcomeAcked(account_id, timestamp, outcome_id)` event to [`praxis/core/domain/events.py`](praxis/core/domain/events.py); registered in [`EventSpine`](praxis/infrastructure/event_spine.py) `_EVENT_REGISTRY`; no-op in [`TradingState.apply`](praxis/core/trading_state.py). Add [`Launcher._append_outcome_acked`](praxis/launcher.py) invoked from the `process_outcome` closure after `OutcomeProcessor.process` returns success — the durable consumption marker that future boot replay-from-spine will use as the un-acked filter (round-18 MAJOR-004 part B)
- Add [`ExecutionManager._dispatch_outcome_with_retry`](praxis/core/execution_manager.py) shared helper replacing all three `_on_trade_outcome` swallow-and-log call sites (`_emit_orphan_rejection`, `_emit_ws_outcome`, `_build_outcome`); bounded retry up to `_OUTCOME_CALLBACK_MAX_ATTEMPTS=3` with exponential backoff `_OUTCOME_CALLBACK_BASE_DELAY=0.5` before exhausting, with the `TradeOutcomeProduced` spine record as the durable evidence on full failure (round-18 MAJOR-004 part B)
- Add `StaleMarketDataError` to [`MarketDataPoller`](praxis/market_data_poller.py); per-cache `fetched_at` stamp on `_fetch` success; `max_age_seconds: dict[int, float]` constructor override (default `2 * kline_size`); `get_market_data` raises on stale; `is_stale(kline_size)` non-raising checker; cleanup hooks in `stop` and `remove_kline_size` (round-18 MAJOR-005)
- Add `StaleMarketDataError` swallow + fall-through in [`_last_close_from_poller`](praxis/launcher.py); when every kline_size is empty or stale the helper returns `None` so the validator's PRICE stage rejects ENTERs cleanly instead of sizing against ancient prices (round-18 MAJOR-005 M05.5)
- Add `recover_orphaned_order` invocation in the [`process_outcome`](praxis/launcher.py) no-context terminal cleanup branch so the orphan order tracked in Nexus `_orders[command_id]` is released alongside the registry pops (round-18 MAJOR-003 M03.1 cross-repo wiring)
- Add 12 deferred-finding entries (TD-040..TD-051) to [`docs/TechnicalDebt.md`](docs/TechnicalDebt.md) covering: EventSpine SQLite PRAGMAs (TD-040); per-outcome `append_mutation` failure not escalated (TD-041); `_reconcile_account` does not query venue open orders absent from spine (TD-042); cross-repo state mismatch undetected at boot (TD-043); shutdown EXIT silently fails when launcher loop is dead (TD-044); symbol filters not loaded for fresh accounts (TD-045); MARKET ENTER reservation lacks slippage buffer (TD-046); no boot-time venue free-balance probe (TD-047); command routing keyed by `command_id` only (TD-048); no multi-account integration test for outcome routing (TD-049); EventSpine `account_id` payload-only (TD-050); `PlatformLimitsStageLimits` constructed empty in launcher (TD-051)
- Add 2 scope-deferral TD entries (TD-052, TD-053) to [`docs/TechnicalDebt.md`](docs/TechnicalDebt.md): boot replay-from-spine for unconsumed `TradeOutcomeProduced` events requires `OutcomeTranslator` determinism prework (TD-052); HealthLoop demote to REDUCE_ONLY on sustained market-data failure requires `HealthSnapshot` field plumbing (TD-053)
- Add 2 pre-PR / PR-review TD entries (TD-054, TD-055) to [`docs/TechnicalDebt.md`](docs/TechnicalDebt.md): the synchronous-block tax on `_append_outcome_acked` under loop overload (TD-054); `_rescue_by_client_order_id` returns `immediate_fills=()` even when the rescued order is FILLED / partially-filled — currently relies on WS reconcile to back-fill the missing fill information (TD-055)
- Add new test files: [`test_launcher_trade_mode.py`](tests/test_launcher_trade_mode.py) (6 tests pinning `_resolve_trade_mode`); [`test_binance_adapter_post_order_rescue.py`](tests/test_binance_adapter_post_order_rescue.py) (5 tests pinning POST timeout + duplicate-clientOrderId rescue triggers); [`test_execution_manager_rescue.py`](tests/test_execution_manager_rescue.py) (5 tests pinning rescue-by-clientOrderId behavior); [`test_launcher_orphan_recovery_wiring.py`](tests/test_launcher_orphan_recovery_wiring.py) (1 AST test pinning `recover_orphaned_order` wiring); [`test_execution_manager_filter_orphan.py`](tests/test_execution_manager_filter_orphan.py) (6 tests pinning filter-violation REJECTED + intent-without-followup orphan); [`test_execution_manager_outcome_retry.py`](tests/test_execution_manager_outcome_retry.py) (4 tests pinning `_dispatch_outcome_with_retry`); [`test_launcher_outcome_acked_wiring.py`](tests/test_launcher_outcome_acked_wiring.py) (1 AST test pinning `_append_outcome_acked` wiring); [`test_market_data_poller_freshness.py`](tests/test_market_data_poller_freshness.py) (10 tests pinning cache freshness + fallback guard)

### Fix

- Fix [`BinanceAdapter`](praxis/infrastructure/binance_adapter.py) order POST retrying transport-level failures with the same `client_order_id` — pre-fix a TimeoutError after the venue had accepted left the retry POSTing a duplicate that Binance returned as `-2010`, classified as REJECTED, while the original order stayed live and the translator's `terminal_emitted` state suppressed the eventual late fill (round-18 MAJOR-002)
- Fix [`BinanceAdapter._validate_order`](praxis/infrastructure/binance_adapter.py) raising plain `ValueError` for filter violations — pre-fix the ValueError escaped the `except VenueError` branch and the worker's broad `except Exception` swallowed it; `CommandAccepted` and `OrderSubmitIntent` were persisted but no terminal outcome reached Nexus, capital stayed parked in `in_flight_order_notional`, and `reconcile_orphan_commands` did not flag it because the existing logic counted `OrderSubmitIntent` as a "follow-up" (round-18 MAJOR-007)
- Fix [`ExecutionManager._build_outcome`](praxis/core/execution_manager.py) `on_trade_outcome` callback exception being logged once and swallowed — pre-fix `TradeOutcomeProduced` was durably persisted on the spine but the consumer (Nexus) was unaware of the delivery failure (round-18 MAJOR-004 part B)
- Fix [`MarketDataPoller.get_market_data`](praxis/market_data_poller.py) returning the previous DataFrame indefinitely after `_fetch` swallowed exceptions — strategies and `fallback_price_provider` could trade on hours-old klines after Binance public REST/testnet outages with no signal (round-18 MAJOR-005)
- Fix [`Launcher._append_outcome_acked`](praxis/launcher.py) reaching into `Trading._event_spine` private attribute; switched to the public `Trading.event_spine` property (Greybeard pre-PR review)

## v0.50.0 on 5th of May, 2026

- Add [`.github/workflows/build_image.yml`](.github/workflows/build_image.yml) — builds the existing `Dockerfile` on push to main (and on `workflow_dispatch`), pushes to `ghcr.io/vaquum/praxis` via `docker/login-action@v3` + `docker/build-push-action@v6` with GitHub Actions docker layer caching (`cache-from: type=gha` + `cache-to: type=gha,mode=max`). Tagging: `:sha-<commit>` is always published; `:<version>` (parsed from `pyproject.toml`'s `version = ...` field) and `:main` are published only when `github.ref == 'refs/heads/main'` so a `workflow_dispatch` from a feature branch cannot overwrite the floating tags with a non-main image. Auth uses `secrets.GITHUB_TOKEN` against the calling workflow's identity. Mirrors the build-job pattern from `Vaquum/experiment_runner`'s `deploy.yml` minus the deploy-to-host step (deferred until the operator runbook for `/opt/praxis/` lands)
- Bump `vaquum-nexus` git+https pin from Nexus 0.38.0 main HEAD `1097d18e7e5a29ffcb212dee33b703e31f5c39ac` to Nexus 0.39.0 main HEAD `52ed0f0a4b7859b941191f85b73f4aaa22911226` (Vaquum/Nexus#59 — example `logreg_binary_evsfd` strategy + manifest + README for paper-trade bring-up under `examples/`)

## v0.51.0 on 5th of May, 2026

- Bump `vaquum_limen` git+https pin from `v2.4.3` to `v3.0.1`. Limen v3 introduced a Manifest API rename (RFC-1004) and a class-based `limen.targets` module replacing the v2 function-based target builders. **Praxis production code does not import from `limen` directly** (verified via `grep -rn "^from limen\|^import limen" praxis/` — zero hits), so no Praxis code change is required; the pin bump propagates to the Docker image so Praxis's bundled Nexus runtime resolves to the same Limen version Nexus pins independently. SFD modules feeding Nexus's `Trainer` (e.g. the `BtcLogRegEVSFD` example bundle) must be re-trained against v3 limen via `experiment_runner` before paper-trade deploy; the bundle re-train is upstream and decoupled from this pin bump
- Bump `vaquum-nexus` git+https pin from Nexus 0.39.0 main HEAD `52ed0f0a4b7859b941191f85b73f4aaa22911226` to Nexus 0.40.0 main HEAD `f4cfa059554cf30c26a45ead7af56ca6501d1674` (Vaquum/Nexus#60 — Limen v3.0.1 pin bump + 10-test `Trainer` integration-contract suite covering `__init__` / `train` parameter names, kinds, defaults, return type via `typing.get_type_hints` + `get_origin` / `get_args`, and `_data` / `_manifest` private-attribute assignments via AST walk of `inspect.getsource(Trainer.__init__)`)

## v0.52.0 on 5th of May, 2026

### Add

- Add WebSocket-API user-data-stream subscription flow to [`BinanceUserStream`](praxis/infrastructure/binance_ws.py) replacing the retired REST listen-key endpoints. New [`_subscribe`](praxis/infrastructure/binance_ws.py) helper sends a signed `userDataStream.subscribe.signature` request frame (HMAC-SHA256 over alphabetically-sorted `apiKey` / `recvWindow` / `timestamp` params), awaits the ack within `_SUBSCRIBE_ACK_TIMEOUT_SECONDS = 10.0`, and stores `subscriptionId` for the unsubscribe-on-close path. [`_clean_setup_connection`](praxis/infrastructure/binance_ws.py) opens the WS-API connection, calls `_subscribe`, and tears down the local ws on subscribe failure. [`_receive_loop`](praxis/infrastructure/binance_ws.py) peels the WS-API `{"event": {...}}` envelope before dispatching to `on_message`; non-event frames are debug-logged and skipped. [`close`](praxis/infrastructure/binance_ws.py) sends `userDataStream.unsubscribe` with `params: {subscriptionId: <id>}` (best-effort) before closing the ws. Subscribe ack validation rejects non-TEXT frames, non-JSON payloads, non-200 status, missing `subscriptionId`, and `bool` values that would otherwise pass `isinstance(int)` (Greybeard pre-PR review)
- Add `MAINNET_WS_API_URL = 'wss://ws-api.binance.com:443/ws-api/v3'` and `TESTNET_WS_API_URL = 'wss://ws-api.testnet.binance.vision/ws-api/v3'` to [`praxis/infrastructure/binance_urls.py`](praxis/infrastructure/binance_urls.py); both exported via `__all__`
- Add `ws_api_url: str` constructor parameter to [`BinanceAdapter`](praxis/infrastructure/binance_adapter.py) stored as `self._ws_api_url`; consumed by `BinanceUserStream._clean_setup_connection` to pick the WS-API endpoint
- Add `venue_ws_api_url: str = TESTNET_WS_API_URL` field to [`TradingConfig`](praxis/trading_config.py) with non-empty validation in `__post_init__`; defaults to testnet so existing test fixtures keep working
- Add WS-API URL to [`_resolve_trade_mode`](praxis/launcher.py) return tuple — now `(rest_url, ws_url, ws_api_url, testnet_flag)` — and thread `venue_ws_api_url` into `TradingConfig` and into the `BinanceAdapter` constructor inside [`Trading.__init__`](praxis/trading.py); operators using `TRADE_MODE=paper` / `TRADE_MODE=live` automatically pick the matching WS-API URL with no env-var surface change
- Add [`docs/TechnicalDebt.md`](docs/TechnicalDebt.md) entry TD-059 (`BinanceUserStream._clean_setup_connection` leaks freshly-opened ws on `CancelledError` between `ws_connect` and `self._ws = ws` assignment; pre-existing pattern preserved from listen-key-era code)

### Fix

- Fix [`BinanceUserStream`](praxis/infrastructure/binance_ws.py) crashlooping on container start with HTTP 410 from `POST /api/v3/userDataStream` — Binance retired the listen-key REST endpoints (`POST` / `PUT` / `DELETE /api/v3/userDataStream`) and now requires WS-API `userDataStream.subscribe.signature` over the WS-API connection. Removed [`_create_listen_key`](praxis/infrastructure/binance_adapter.py), [`_keepalive_listen_key`](praxis/infrastructure/binance_adapter.py), [`_close_listen_key`](praxis/infrastructure/binance_adapter.py) and the now-orphaned [`_api_key_request`](praxis/infrastructure/binance_adapter.py) helper from `BinanceAdapter`. Removed `_keepalive_loop`, `_keepalive_task`, `_listen_key`, `keepalive_interval_seconds`, `_DEFAULT_KEEPALIVE_INTERVAL_SECONDS`, and `_build_ws_url` from `BinanceUserStream` — the WS-API connection multiplexes subscribe + push events on the same socket and aiohttp's auto-pong handles the 20s server pings, so no separate keepalive task is required (closes #93)
- Fix lint drift in pre-existing test fixtures: `asyncio.TimeoutError` → builtin `TimeoutError` in [`praxis/infrastructure/binance_ws.py`](praxis/infrastructure/binance_ws.py) and [`tests/test_binance_ws.py`](tests/test_binance_ws.py); `__all__` sort order in [`praxis/infrastructure/binance_urls.py`](praxis/infrastructure/binance_urls.py) (Greybeard pre-PR review)

## v0.53.0 on 6th of May, 2026

- Bump `vaquum_limen` git+https pin from `v3.0.1` to `v3.0.3` ([Vaquum/Limen#500](https://github.com/Vaquum/Limen/pull/500)). Limen v3.0.3 makes [`Trainer.__init__`](https://github.com/Vaquum/Limen/blob/v3.0.3/limen/experiment/trainer/trainer.py) hermetic per-experiment: the SFD module named by `metadata.json["sfd_module"]` is now loaded by preferring a `<sfd_module>.py` file inside `experiment_dir` (via `importlib.util.spec_from_file_location` + `module_from_spec`, no `sys.path` mutation) before falling back to `importlib.import_module`, with path-traversal hardening (segment-by-segment `isidentifier()` validation) on the name. **Praxis production code does not import from `limen` directly** (verified via `grep -rn "^from limen\|^import limen" praxis/` — zero hits), so no Praxis code change is required; the pin bump propagates to the Docker image so Praxis's bundled Nexus runtime resolves to the same Limen version Nexus pins independently
- Bump `vaquum-nexus` git+https pin from Nexus 0.40.0 main HEAD `f4cfa059554cf30c26a45ead7af56ca6501d1674` to Nexus 0.42.0 main HEAD `6c80d2768faa9b0dfec5f11b95b4f4bb0e710db3` ([Vaquum/Nexus#62](https://github.com/Vaquum/Nexus/pull/62) — the Limen v3.0.3 pin bump + comment refresh + `examples/README.md` SFD-loading guidance update; also includes [Vaquum/Nexus#61](https://github.com/Vaquum/Nexus/pull/61), `PredictLoop.tick_once` synchronous single-shot entry point, which Praxis's Timer-driven runtime does not call but which lands in the same image)
- Unblocks the deployment-server paper-trade smoke for the `BtcLogRegEVSFD` experiment_dir bundle staged at `/var/lib/praxis/experiments/BtcLogRegEVSFD/` (with `metadata.json["sfd_module"] = "BtcLogRegEVSFD__r0001"` and `BtcLogRegEVSFD__r0001.py` co-located in the dir) — pre-bump the v0.52.0 image crashlooped at `nexus/startup/sequencer.py:626` with `ModuleNotFoundError: No module named 'BtcLogRegEVSFD__r0001'` because Limen v3.0.1 only resolved the SFD name via `import_module` against `sys.path` and the launcher's `STRATEGIES_BASE_PATH` does not include the experiment directories. Under Limen v3.0.3 the local-file-first branch loads the SFD directly from `experiment_dir`, with no operator-side `PYTHONPATH` wiring required and no SFD-file copying into `manifests/`

## v0.54.0 on 7th of May, 2026

- Bump `vaquum_limen` git+https pin from `v3.0.3` to `v3.0.5` ([Vaquum/Limen#505](https://github.com/Vaquum/Limen/pull/505)). Limen v3.0.5 fixes the experiment-local SFD load to register the loaded module in `sys.modules` (with rollback on `exec_module` failure) so downstream `importlib.import_module(architecture_function.__module__)` lookups (notably Limen's own `Trainer._resolve_model_class`) resolve to the same module instance. Without this, self-contained bundles (e.g. `BtcLogRegEVSFD`-style experiment_dirs whose architecture function is defined inside the SFD file) reached `Trainer.__init__` cleanly but failed at `train()` → `_resolve_model_class()` with `ModuleNotFoundError`. **Praxis production code does not import from `limen` directly** (verified via `grep -rn "^from limen\|^import limen" praxis/` — zero hits), so no Praxis code change is required; the pin bump propagates to the Docker image so Praxis's bundled Nexus runtime resolves to the same Limen version Nexus pins independently
- Bump `vaquum-nexus` git+https pin from Nexus 0.42.0 main HEAD `6c80d2768faa9b0dfec5f11b95b4f4bb0e710db3` to Nexus 0.43.0 main HEAD `81088b977d855c15da0a5a97c8339f79e30ce0ce` ([Vaquum/Nexus#63](https://github.com/Vaquum/Nexus/pull/63) — the Limen v3.0.5 pin bump on the Nexus side + comment refresh + `examples/README.md` SFD-load guidance update)
- Unblocks the deployment-server paper-trade smoke for the `BtcLogRegEVSFD` experiment_dir bundle at the `_resolve_model_class` path; the cp-to-`manifests/` operator workaround the v0.53.0 deploy needed (because Limen v3.0.3 didn't register the experiment-local SFD module in `sys.modules`) is no longer required after this propagates downstream

## v0.55.0 on 10th of May, 2026

- Bump `vaquum-nexus` git+https pin from Nexus 0.43.0 main HEAD `81088b977d855c15da0a5a97c8339f79e30ce0ce` to Nexus 0.44.0 main HEAD `33aa205d57dc37c9df6cbe021dc563f261e71220` ([Vaquum/Nexus#64](https://github.com/Vaquum/Nexus/pull/64)). Nexus v0.44.0 fixes [`signal_producer.produce_signal`](https://github.com/Vaquum/Nexus/blob/v0.44.0/nexus/strategy/signal_producer.py) to pass the last `lookback` rows to `sensor.predict` as a `polars.DataFrame` instead of `numpy.ndarray`. The pre-fix `x_train.tail(lookback).to_numpy()` discarded column names, defeating SFDs that defend against feature-shape drift by selecting `_model_columns` from the live frame at predict time (e.g. the `BtcLogRegEVSFD` bundle, which records `self.model_cols` at fit time and calls `frame.select(self.model_cols)` in `_raw_probs`). When the predict-time frame had columns the training-time frame did not — specifically `binancial.compute.get_spot_klines`'s 19 input columns vs the HF dataset's 17 (`median`, `iqr` extra) — the SFD's numpy-branch shape check `x.shape[1] == len(self.training_feature_columns)` (`80 != 78`) skipped the index-based slice and forwarded all 80 columns to `LogisticRegression.predict_proba` which expected 77, raising `ValueError: X has 80 features, but LogisticRegression is expecting 77 features as input` on every sensor tick. **Praxis production code does not import from `nexus.strategy.signal_producer` directly** (verified via `grep -rn "from nexus.strategy.signal_producer\|import nexus.strategy.signal_producer" praxis/` — zero hits); the bundled Nexus runtime in the Docker image consumes the fix transparently when the launcher's predict loop dispatches sensor ticks
- Unblocks the deployment-server paper-trade `BtcLogRegEVSFD_5m_v3` bundle (5-minute kline variant staged at `/var/lib/praxis/experiments/BtcLogRegEVSFD_5m_v3_100permut/`) where every sensor tick at the configured 300s interval was hitting the column-mismatch `ValueError` in production. With the fix propagated through the v0.55.0 image, the SFD's `pl.DataFrame` branch (`x = _frame_to_numpy(frame, self.model_cols)`) selects the trained 77 columns by name and ignores the live-data extras, harmonising the live and training paths on the same input shape. Limen v3.0.5 pin unchanged

## v0.56.0 on 10th of May, 2026

- Bump `vaquum_limen` git+https pin from `v3.0.5` to `v3.0.6` ([Vaquum/Limen#507](https://github.com/Vaquum/Limen/pull/507)). Limen v3.0.6 adds `end_date_limit` and `row_count_limit` (canonical name; legacy `n_rows` retained as alias) parameters to [`HistoricalData.get_spot_klines`](https://github.com/Vaquum/Limen/blob/v3.0.6/limen/data/historical_data.py) and `HistoricalData.get_any_file`. With both `start_date_limit` and `end_date_limit` set the data window is fully closed and reproducible across the daily HF dataset snapshot growth, which lets SFD bundles fix a deterministic training window so `Trainer.train()`'s Pass 1 strict reconstruction check no longer trips on day-to-day metric drift. **Praxis production code does not import from `limen` directly** (verified via `grep -rn "^from limen\|^import limen" praxis/` — zero hits); the only Limen consumer in the dep tree is Nexus. The Praxis Limen pin matters for **dep-tree coherence**: `pip install vaquum-praxis` resolves both Praxis's own Limen pin and Nexus's Limen pin from `vaquum-praxis -> vaquum-nexus -> vaquum_limen`, and since both are git+https URLs (not version constraints), pip cannot dedupe by version. Keeping Praxis and Nexus on the same Limen pin keeps the resolver deterministic
- Bump `vaquum-nexus` git+https pin from Nexus 0.44.0 main HEAD `33aa205d57dc37c9df6cbe021dc563f261e71220` to Nexus 0.45.0 main HEAD `1e3c0700f0954ae49641484ecfada2d625d0b11c` ([Vaquum/Nexus#65](https://github.com/Vaquum/Nexus/pull/65) — the Limen v3.0.6 pin bump on the Nexus side + comment refresh)
- Unblocks the deployment-server paper-trade `BtcLogRegEVSFD_5m_v3` deploy at the `ReconstructionError` path observed at sensor-wiring time after the v0.55.0 image landed. Pre-3.0.6 the bundle's `set_data_source` only supported `start_date_limit`, so each container start re-trained against a slightly-newer HF snapshot than the one we ran the UEL on (HF dataset is daily-snapshotted), tripping Pass 1's strict equality check on `bars_total` / `backtest_*` drift (`backtest_total_return_net_pct: original=4.1, new=-9.5`; `backtest_bars_total: original=44543, new=44595`). With v3.0.6 a future re-run of the UEL pinning `start_date_limit='2024-01-01', end_date_limit='<fixed date>'` produces a deterministic results.csv that survives daily HF refresh

## v0.57.0 on 10th of May, 2026

- Bump `vaquum-nexus` git+https pin from Nexus 0.45.0 main HEAD `1e3c0700f0954ae49641484ecfada2d625d0b11c` to Nexus 0.46.0 main HEAD `b075042aa0cd5aad6da8355ce7d672983fb71eb1` ([Vaquum/Nexus#66](https://github.com/Vaquum/Nexus/pull/66)). Nexus v0.46.0 fixes [`signal_producer.produce_signal`](https://github.com/Vaquum/Nexus/blob/v0.46.0/nexus/strategy/signal_producer.py) to support `RuleBasedManifest` SFDs alongside `MLManifest`. The predict path was previously hard-coded against the `MLManifest.prepare_data` output shape — `data_dict.get('x_train')` for the live train frame and `wired.sensor.predict({'x_test': ...})` for the predict call — but `RuleBasedManifest.prepare_data` returns `{'train', 'val', 'test', '_alignment', 'strategy'}` with no `x_train` / `x_test` keys, so every rule-based sensor tick raised `ValueError: prepare_data returned no x_train for sensor <id>` on the empty-train guard. Post-fix, `produce_signal` branches on `isinstance(wired.limen_manifest, RuleBasedManifest)` and pulls `train` / passes `test` for that path. ML-SFDs are unaffected. **Praxis production code does not import from `nexus.strategy.signal_producer` directly** (verified via `grep -rn "from nexus.strategy.signal_producer\|import nexus.strategy.signal_producer" praxis/` — zero hits); the bundled Nexus runtime in the Docker image consumes the fix transparently when the launcher's predict loop dispatches sensor ticks
- Unblocks the deployment-server paper-trade stub-strategy bundle (`StubStrategySFD` with four trivial sub-strategies — `always_one`, `always_zero`, `alternating`, `coin_toss` — staged at `/var/lib/praxis/experiments/StubStrategySFD_4permut/`) where every sensor tick at the configured 900s (15-minute) interval was hitting the empty-train guard in production. With the fix propagated through the v0.57.0 image, all four stubs tick cleanly through the rule-based predict path and the operator can validate the executor end-to-end on signal patterns the existing `BtcLogRegEVSFD` (which sits HOLD silently) does not exercise. Limen v3.0.6 pin unchanged

## v0.58.0 on 10th of May, 2026

- Add `translate_order_side`, `translate_order_type`, `translate_execution_mode`, `translate_maker_preference`, and `translate_stp_mode` helpers to [`praxis/command_translator.py`](praxis/command_translator.py). Each helper re-keys a foreign enum member to the matching Praxis [`praxis.core.domain.enums`](praxis/core/domain/enums.py) member by `.value`, raising `TypeError` if the input lacks a string `.value` and `ValueError` if the value has no Praxis equivalent. Praxis members pass through identity-equal so callers that already hold Praxis enums pay no overhead
- Wire the new translators into [`launcher.py`](praxis/launcher.py)'s `submit_command_with_translated_params` so every Nexus `TradeCommand` enum (`side`, `order_type`, `execution_mode`, `maker_preference`, `stp_mode`) is rebuilt as the Praxis enum member before the call reaches `Trading.submit_command`. Without this, `validate_trade_command` (called inside `ExecutionManager.submit_command`) rejected every order with `no allowed order types configured for mode SINGLE_SHOT` because `_ALLOWED_ORDER_TYPES.get(cmd.execution_mode)` returned `None` — the dict is keyed by Praxis `ExecutionMode` members but `cmd.execution_mode` was a Nexus `ExecutionMode` instance with the same `.value` but a different class identity. The same hidden-class-mismatch trap silently bypassed `TradeCommand.__post_init__`'s `self.execution_mode is ExecutionMode.SINGLE_SHOT` identity check (so the `isinstance(execution_params, SingleShotParams)` invariant was not enforced for Nexus-shape commands) and would also have skipped `_validate_maker_preference` for any Nexus-side `MAKER_ONLY` order
- Add `_STP_MODE_VALUE_MAP` (`CANCEL_MAKER` → `EXPIRE_MAKER`, `CANCEL_TAKER` → `EXPIRE_TAKER`, `CANCEL_BOTH` → `EXPIRE_BOTH`) so `translate_stp_mode` carries Nexus's [`nexus.core.stp_mode.STPMode`](https://github.com/Vaquum/Nexus/blob/v0.46.0/nexus/core/stp_mode.py) onto the equivalent Praxis [`STPMode`](praxis/core/domain/enums.py) member. Nexus and Praxis are the only enum pair whose value strings disagree (Nexus uses `CANCEL_*`, Praxis uses `EXPIRE_*`) so without the map a generic value-lookup translation would silently throw on every command that carries the Praxis-default `stp_mode`
- Add 16 new tests to [`test_command_translator.py`](tests/test_command_translator.py) covering: each translator passes Praxis members through identity-equal; each translator re-keys a synthetic foreign enum (defined in-file to avoid coupling tests to Nexus internals) to the Praxis member; `STPMode` carries the three `CANCEL_*` → `EXPIRE_*` semantic mappings; and unknown values / non-enum inputs raise `ValueError` / `TypeError` respectively
- Unblocks the deployment-server paper-trade stub-strategy bundle (`StubStrategySFD_4permut`) where the four `always_one` / `always_zero` / `alternating` / `coin_toss` sensors finally produced ENTER actions through the rule-based predict path (post-v0.57.0) but each command was rejected at `validate_trade_command` before it could reach the `BinanceAdapter`. Pre-fix `praxis-1` logs showed `no allowed order types configured for mode SINGLE_SHOT` on every signal tick; post-fix the same UEL routes through `submit_command_with_translated_params` → translated Praxis enums → `validate_trade_command` → `BinanceAdapter.submit_order`. The original `BtcLogRegEVSFD` bundle never tripped this validator because its strategy file's `_reference_price(signal)` already short-circuits on the missing `signal.get('close')` field, so the enum-translation gap was masked end-to-end until the stub bundle started actually firing actions

## v0.58.1 on 10th of May, 2026

- Patch [`translate_maker_preference`](praxis/command_translator.py) and [`translate_stp_mode`](praxis/command_translator.py) in [`praxis/command_translator.py`](praxis/command_translator.py) to substitute `None` with the matching Praxis enum default (`MakerPreference.NO_PREFERENCE` and `STPMode.NONE`, respectively) instead of forwarding `None` to `_translate_enum` and crashing with `TypeError: maker_preference must be MakerPreference or an enum with a string .value, got NoneType`. The strict three (`translate_order_side`, `translate_order_type`, `translate_execution_mode`) keep their `None`-rejecting behaviour because the corresponding Nexus [`Action`](https://github.com/Vaquum/Nexus/blob/v0.46.0/nexus/strategy/action.py) fields are guaranteed non-`None` at the ENTER boundary by `Action._validate_action_type_requirements`. Pre-patch `submit_command_with_translated_params` raised `TypeError` on every Nexus `Action` whose strategy did not set `maker_preference` — observed on the deployment server at `2026-05-10T14:31:57Z` for all four `StubStrategySFD_4permut` sensors after the v0.58.0 image landed. Substituting at the boundary keeps the downstream `Trading.submit_command` type contract honest (Praxis enums all the way down, no `Optional` widening of public submit signatures) while preserving the implicit pre-v0.58.0 "no opinion / no STP" semantics
- Update [`tests/test_command_translator.py`](tests/test_command_translator.py): add `test_translate_maker_preference_substitutes_no_preference_for_none`, `test_translate_stp_mode_substitutes_none_member_for_none`, and three `test_translate_*_rejects_none` cases (one per strict translator) pinning the new contracts so a future refactor can re-introduce neither the v0.58.0 deployment-server crash nor an accidental `None` passthrough on a strict field. Foreign-enum re-keying, `STPMode` semantic mapping (`CANCEL_*` → `EXPIRE_*`), and the `TypeError` path for non-`None` non-enum inputs (`translate_order_side('BUY')`) remain unchanged

## v0.59.0 on 11th of May, 2026

- Add `_snap_qty_to_lot_step` helper in [`praxis/infrastructure/binance_adapter.py`](praxis/infrastructure/binance_adapter.py) and call it at the top of `submit_order` so the order quantity is rounded down to the symbol's cached LOT_SIZE step before reaching `_validate_order` and the Binance REST endpoint. Pre-patch the deployment server hit `Order rejected: Illegal characters found in parameter 'quantity'; legal range is '^([0-9]{1,20})(\.[0-9]{1,20})?$'. (code -1100)` on every stub-strategy ENTER tick (observed at `2026-05-10T17:59:03Z` for all four `StubStrategySFD_4permut` sensors after the v0.58.1 image landed): Nexus strategies size ENTER as `notional / reference_price` with no quantization, which produces a `Decimal` carrying the full `getcontext().prec` (default 28) digits — `Decimal('20') / Decimal('81458')` resolves to `0.0002455253013823074467823909254` (31 fractional digits) and `format(qty, 'f')` faithfully renders all of them, overflowing the venue's 20-fractional-digit cap. Snaps via `(qty // lot_step) * lot_step` (floor-divide-then-multiply), not `Decimal.quantize(lot_step, ...)` — `quantize` rounds to the *exponent* of `lot_step` rather than to an integer multiple of it, so `Decimal('0.0002455…').quantize(Decimal('0.00001000'), ROUND_DOWN)` would have produced `0.00024552` (eight fractional digits, neither a multiple of `0.00001` nor accepted by Binance's LOT_SIZE filter). Binance's `exchangeInfo` returns `stepSize='0.00001000'` (exponent `-8`) for BTCUSDT, so the trailing-zero shape is the production case, not a hypothetical. Floor-divide-then-multiply is exact for any `lot_step` shape including non-pure-`10^-n` steps. The snap is a no-op when the symbol's filters are not cached (returns `qty` unchanged), so the existing "No cached filters for X, skipping validation" warning path remains the single signal for a missing filter cache rather than being masked by a silent fallback
- Add `bootstrap_filter_symbols: frozenset[str] = frozenset()` to [`Trading.__init__`](praxis/trading.py) and merge it into the symbol set passed to `VenueAdapter.load_filters` from `_startup_account`. Pre-patch the deployment server logged `No cached filters for BTCUSDT, skipping validation` ahead of every venue submission because [`ExecutionManager.active_symbols`](praxis/core/execution_manager.py) only returns symbols with open orders or positions, which is the empty set on a fresh paper-trade boot — so `load_filters([])` was a no-op, the LOT_SIZE / PRICE / NOTIONAL invariants in `_validate_order` were silently bypassed, and the strategy-supplied high-precision qty reached Binance unsnapped. Wire [`praxis/launcher.py`](praxis/launcher.py) to construct `Trading(...)` with `bootstrap_filter_symbols=frozenset({_DEFAULT_SYMBOL})` so `BTCUSDT` filters are loaded before any sensor can fire its first ENTER action
- Make [`BinanceAdapter.load_filters`](praxis/infrastructure/binance_adapter.py) idempotent: skip symbols already present in `_filters` instead of unconditionally overwriting. `_startup_account` runs `load_filters(union(active_symbols, bootstrap_filter_symbols))` per account, so without the skip every multi-account boot would refetch `exchangeInfo` for the bootstrap symbol once per account — N venue weight units and N round-trips of startup latency for nothing, since per-symbol filter values are deploy-gated and immutable within a process lifetime. In-process filter refresh is intentionally unsupported — the only way to pick up new venue filters is to restart the process; if a future use case ever needs in-process refresh, add an explicit method on the `VenueAdapter` protocol rather than mutating private adapter state from outside
- Add `TestSnapQtyToLotStep` with seven cases in [`tests/test_binance_adapter.py`](tests/test_binance_adapter.py) covering: 31-fractional-digit input snaps to `0.00024` on `lot_step=0.00001`; snap floors (never exceeds input); already-aligned qty preserved unchanged; missing-filter symbol returns the input unchanged (no silent quantize-by-default); `submit_order` end-to-end emits a `quantity=0.00024` URL fragment matching Binance's `^([0-9]{1,20})(\.[0-9]{1,20})?$` regex; the venue-wire-format `lot_step=Decimal('0.00001000')` (with trailing zeros, exponent `-8`) snaps to a value that satisfies BOTH the wire-form-modulo and the numeric-multiple-modulo invariants; and a non-power-of-ten step (`lot_step=5`) floors `13` to `10`. The trailing-zero and non-`10^-n` cases pin the floor-divide-then-multiply contract specifically (a `Decimal.quantize(...)` implementation would silently fail both). Add `test_trading_start_preloads_bootstrap_filter_symbols_on_fresh_boot` and `test_trading_start_merges_bootstrap_and_active_symbols` in [`tests/test_trading.py`](tests/test_trading.py) pinning the new `Trading.__init__` kwarg's behaviour on the fresh-boot and replay-with-orders branches respectively. Existing `test_trading_start_preloads_filters_for_active_symbols` left unchanged — the bootstrap set defaults to empty and the historical behaviour is preserved
- Unblocks the deployment-server paper-trade `StubStrategySFD_4permut` bundle past the venue boundary. With v0.59.0 the four stub sensors' next 900s ENTER ticks are expected to: snap qty to `0.00024` on cached `BTCUSDT` filters → pass `_validate_order` invariants → emit a `quantity=0.00024` REST param that matches Binance's regex → receive a venue ACK (the testnet account has BTCUSDT depth; orders will fill or rest depending on order_type). The four sensors share a `MARKET` order_type via [`logreg_binary_evsfd.py`](https://github.com/Vaquum/Praxis/blob/main/manifests/strategies/logreg_binary_evsfd.py) so the expected steady state is immediate fill with the testnet's `lot_step=0.00001` precision. Once an ENTER fills, the strategy's `_exit` path can fire on the next `_preds == 0` tick (for `always_zero`, `alternating`, `coin_toss`) and verify the full ENTER → fill → EXIT → fill → close-position loop end-to-end

## v0.59.1 on 12th of May, 2026

- Anchor [`MarketDataPoller._poll_loop`](praxis/market_data_poller.py)'s fetch cadence to the original schedule (`anchor + n * interval`) instead of resleeping `interval` between fetches, with skip-missed-slots so a multi-interval-overrun fetch does not trigger back-to-back catch-up fetches. Pre-patch the loop did `while not stop_event.wait(timeout=interval): self._fetch(...)` — the wait fired *after* `_fetch` returned, so realized period was `interval + fetch_duration`. On Binance testnet under load `_fetch` regularly takes 200-500s (the `get_spot_klines` HTTP call queues behind rate-limited concurrent requests from the venue adapter), which for `kline_size=300` (5m kline, `interval=300s`) pushed realized period past `_DEFAULT_MAX_AGE_MULTIPLIER * kline_size = 600s` and tripped `StaleMarketDataError` on the next sensor tick — observed on the deployment server at `2026-05-12T07:37:12Z` and recurring every 25-75min thereafter for the `2d9aedcbea82:29` (`logreg_binary_evsfd`) sensor with measured ages of 606-732s. The anchored guarantee is **no cumulative drift**: after each fetch returns, `n` advances to `max(n + 1, int(elapsed // interval) + 1)` so any number of "missed" slots (when a single fetch spans `k > 1` intervals) collapses into a single catch-up fetch at the next future scheduled slot rather than firing `k - 1` back-to-back fetches with `wait(0)`. The freshness goal of skipped slots is moot — the slow fetch's return brings data through `now` — and the post-overrun cadence resumes immediately at the original timeline. `n` slow fetches therefore do not produce `n * overrun` cumulative drift
- Apply the same skip-missed-slots logic to `n`'s initialization after the *initial* fetch: `n = max(1, int(elapsed // interval) + 1)`. Pre-patch this commit hardcoded `n = 1` after the explicit pre-loop fetch, so a slow initial fetch (e.g. cold-cache exchangeInfo round-trip + first historical kline fetch) caused iter 1's `wait_seconds = max(0, 1 * interval - elapsed)` to fall to 0 and fire fetch #2 immediately back-to-back — exactly the burst skip-missed-slots is meant to prevent. Now the initial fetch's overrun follows the same skip rule as every subsequent fetch
- Widen the `interval` type hint from `int` to `float` on [`_PollerThread.interval`](praxis/market_data_poller.py), [`MarketDataPoller.add_kline_size`](praxis/market_data_poller.py), `MarketDataPoller.__init__`'s `kline_intervals: dict[int, float]`, and the internal `_start_thread_locked` / `_poll_loop` signatures. Production callers continue to pass integer seconds (`300`, `900`); the regression tests need sub-second cadences (`0.1`, `0.105`) to actually run in CI time. `kline_size` stays `int` (Binance kline sizes are all integer seconds). Tighten the existing positivity check from `interval <= 0` to `not math.isfinite(interval) or interval <= 0` so the float widening cannot smuggle in `NaN` (slips through `<= 0` because any comparison with NaN is False, then propagates to `wait_seconds = anchor + n * NaN - now = NaN` and breaks `Event.wait`) or `inf` (passes `<= 0`, makes `wait(inf)` block the poller thread forever with no re-fetches). Add `test_add_kline_size_rejects_nan_and_inf_interval` and `test_start_rejects_nan_and_inf_initial_intervals` pinning the new invariant on both validation paths
- Add three regression tests in [`tests/test_market_data_poller.py`](tests/test_market_data_poller.py): `test_slow_fetch_does_not_accumulate_drift_in_fetch_schedule` pins cumulative-no-drift for sub-2-interval overruns (anchored fetch #4 at `4 * interval = 0.40s` vs pre-fix `3 * interval + slow_delay = 0.45s`, threshold `0.425s`); `test_multi_interval_slow_fetch_collapses_missed_slots` pins the in-loop skip behaviour for `slow_delay = 2.5 * interval` (fetch #3 lands at next future slot, not back-to-back with slow return); `test_slow_initial_fetch_skips_to_next_future_slot` pins the initial-fetch skip for `slow_delay = 1.05 * interval` (fetch #2 at next slot `0.20s` vs pre-fix back-to-back at `0.105s`, threshold `0.1525s` with ~`0.045s` margin each side). All three regressions verified locally by swapping the loop body to each pre-state implementation and confirming the corresponding test fails before restoring
