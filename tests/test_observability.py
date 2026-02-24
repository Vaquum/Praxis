'''Verify structlog + orjson logging configuration.'''

from __future__ import annotations

import io
import logging

from typing import Any

import orjson
import structlog

from praxis.infrastructure.observability import (
    bind_context,
    clear_context,
    configure_logging,
    get_logger,
)


def _capture_structlog(func: Any) -> dict[str, Any]:

    '''
    Capture a single structlog log line as a parsed dict.

    Args:
        func (Any): Callable that emits exactly one structlog log line

    Returns:
        dict[str, Any]: Parsed JSON log output
    '''

    buf = io.BytesIO()
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt='iso', utc=True),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer(serializer=orjson.dumps),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.DEBUG),
        logger_factory=structlog.BytesLoggerFactory(file=buf),
        cache_logger_on_first_use=False,
    )
    func()
    result: dict[str, Any] = orjson.loads(buf.getvalue().strip())
    return result


def _capture_stdlib(func: Any) -> dict[str, Any]:

    '''
    Capture a single stdlib log line routed through structlog as a parsed dict.

    Args:
        func (Any): Callable that emits exactly one stdlib log line

    Returns:
        dict[str, Any]: Parsed JSON log output
    '''

    buf = io.StringIO()
    configure_logging('DEBUG')
    root = logging.getLogger()
    handler = logging.StreamHandler(buf)
    for h in root.handlers:
        if hasattr(h, 'formatter') and h.formatter is not None:
            handler.setFormatter(h.formatter)
            break
    root.handlers.clear()
    root.addHandler(handler)

    func()
    result: dict[str, Any] = orjson.loads(buf.getvalue().strip())
    return result


def test_configure_logging_runs() -> None:

    '''Verify configure_logging completes without error.'''

    configure_logging()


def test_configure_logging_accepts_levels() -> None:

    '''Verify all standard log levels are accepted.'''

    for level in ('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'):
        configure_logging(level)


def test_output_is_valid_json() -> None:

    '''Verify logger output is parseable JSON.'''

    result = _capture_structlog(lambda: structlog.get_logger().info('test'))
    assert isinstance(result, dict)


def test_json_contains_required_keys() -> None:

    '''Verify JSON output contains event, level, and timestamp keys.'''

    result = _capture_structlog(lambda: structlog.get_logger().info('test'))
    assert result['event'] == 'test'
    assert result['level'] == 'info'
    assert 'timestamp' in result


def test_timestamp_is_iso8601_utc() -> None:

    '''Verify timestamp is ISO 8601 format ending with Z.'''

    result = _capture_structlog(lambda: structlog.get_logger().info('test'))
    ts = result['timestamp']
    assert ts.endswith('Z')
    assert 'T' in ts


def test_bind_context_appears_in_logs() -> None:

    '''Verify bound context fields appear in log output.'''

    clear_context()
    bind_context(account_id='acc1', epoch_id=1)

    result = _capture_structlog(lambda: structlog.get_logger().info('test'))
    assert result['account_id'] == 'acc1'
    assert result['epoch_id'] == 1

    clear_context()


def test_clear_context_removes_fields() -> None:

    '''Verify clear_context removes all bound fields.'''

    bind_context(account_id='acc1')
    clear_context()

    result = _capture_structlog(lambda: structlog.get_logger().info('test'))
    assert 'account_id' not in result


def test_log_level_filtering() -> None:

    '''Verify DEBUG is suppressed when level is INFO.'''

    buf = io.BytesIO()
    structlog.configure(
        processors=[
            structlog.processors.add_log_level,
            structlog.processors.JSONRenderer(serializer=orjson.dumps),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
        logger_factory=structlog.BytesLoggerFactory(file=buf),
        cache_logger_on_first_use=False,
    )
    structlog.get_logger().debug('should not appear')
    assert buf.getvalue() == b''


def test_get_logger_returns_usable_logger() -> None:

    '''Verify get_logger returns a logger that can emit logs.'''

    configure_logging('DEBUG')
    log = get_logger('praxis.test')
    assert callable(getattr(log, 'info', None))
    assert callable(getattr(log, 'warning', None))
    assert callable(getattr(log, 'error', None))


def test_stdlib_integration() -> None:

    '''Verify stdlib logging produces structlog JSON output.'''

    result = _capture_stdlib(
        lambda: logging.getLogger('aiohttp').warning('connection reset')
    )
    assert result['event'] == 'connection reset'
    assert result['level'] == 'warning'
    assert 'timestamp' in result
