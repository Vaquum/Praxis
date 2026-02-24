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
