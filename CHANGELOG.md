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
- Add [`Dockerfile`](Dockerfile) (Python 3.10-slim, installs `git` for git-sourced deps, non-root `praxis` user, entrypoint `python -m praxis.launcher`) and [`.dockerignore`](.dockerignore)
- Add [`render.yaml`](render.yaml) blueprint — single Render Web service, `region: singapore`, `plan: starter`, `numInstances: 1`, `autoDeploy: false`, `healthCheckPath: /healthz`, 10 GB persistent disk mounted at `/var/lib/praxis`. Per-account secrets declared `sync: false`
- Add `/healthz` endpoint on the launcher's asyncio loop via `aiohttp`: returns 200 when `Trading.started`, the loop thread is alive, `_stop_event` is unset, and every Nexus thread is alive; 503 with a `failures:` list otherwise. Stopped first in `_shutdown` so Render sees unhealthy immediately on `SIGTERM`. `Launcher.__init__` gains optional `healthz_port: int | None = None`
- Resolve `/healthz` bind port from `PORT` (Render-injected), then `HEALTHZ_PORT`, then default `8080`. Guard signal-handler registration on `threading.main_thread()` so tests can drive `launch()` from a worker thread
- Route launcher `main()` logging through [`observability.configure_logging`](praxis/infrastructure/observability.py) (structlog + orjson JSON to stdout) when `LOG_FORMAT=json` (default); `LOG_FORMAT=text` falls back to stdlib `basicConfig` for local dev. `bind_context(epoch_id=...)` before `Launcher.launch()` so every record carries `epoch_id`
- Add optional `db_path: Path | None = None` to `Launcher`; when set, opens an `aiosqlite` connection on its own loop and builds the `EventSpine` internally (mutually exclusive with the caller-built `event_spine` path). Connection closed during shutdown
- Migrate [`MarketDataPoller`](praxis/market_data_poller.py) off `tdw_control_plane.query.get_binance_spot_klines` to `binancial.compute.get_spot_klines` (Binancial commit `634d5bd`). Lazily build `binance.client.Client(None, None)` for public klines (no credentials needed); compute `start_date` as `now - n_rows * kline_size` seconds; convert the returned pandas DataFrame to polars. Swap `pyproject.toml` dep `quickstart_etl @ git+.../tdw-control-plane` → `binancial @ git+.../Binancial`
- Lift delayed `import polars as pl` to the top of [`praxis/launcher.py`](praxis/launcher.py)
- Add [`docs/Deployment-Render.md`](docs/Deployment-Render.md) with full Render deployment runbook; rewrite [`docs/Launcher.md`](docs/Launcher.md) for the multi-account env-driven entrypoint + `/healthz` + JSON logging; add a "Two Different Health Concepts" section to [`docs/Health.md`](docs/Health.md) distinguishing `HealthSnapshot` from `/healthz`; list the new deployment guide in [`docs/README.md`](docs/README.md)
- Add [`tests/test_launcher_healthz.py`](tests/test_launcher_healthz.py) (healthy-path + shutdown-path) and [`tests/test_launcher_json_logging.py`](tests/test_launcher_json_logging.py) (JSON parseable, bound-context field, text-fallback). Update [`tests/test_launcher.py`](tests/test_launcher.py) `_make_manifest_yaml` to emit the required `account_id:` + `allocated_capital:` fields and drop `allocated_capital=` from `InstanceConfig(...)` call sites
- Add 5 tests across `test_launcher_healthz.py` and `test_launcher_json_logging.py` (776 total)
