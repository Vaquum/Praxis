'''
Structured logging configuration for Praxis.

Configures structlog with orjson serialization, asyncio-safe context
variable binding, and ISO 8601 UTC timestamps. Call configure_logging()
once at process startup before any other initialization.
'''

from __future__ import annotations

import logging
import sys
from typing import Any

import orjson
import structlog

__all__ = ['bind_context', 'clear_context', 'configure_logging', 'get_logger']


def _orjson_dumps_str(*args: Any, **kwargs: Any) -> str:

    '''
    Serialize to JSON string via orjson for stdlib ProcessorFormatter.

    Returns:
        str: JSON-encoded string
    '''

    return orjson.dumps(*args, **kwargs).decode()


def configure_logging(log_level: str = 'INFO') -> None:

    '''
    Configure structlog with orjson JSON rendering to stdout.

    Args:
        log_level (str): Minimum log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)

    Returns:
        None
    '''

    numeric_level = getattr(logging, log_level.upper(), logging.INFO)

    shared_processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt='iso', utc=True),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
    ]

    structlog.configure(
        processors=[
            *shared_processors,
            structlog.processors.JSONRenderer(serializer=orjson.dumps),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(numeric_level),
        logger_factory=structlog.BytesLoggerFactory(),
        cache_logger_on_first_use=True,
    )

    formatter = structlog.stdlib.ProcessorFormatter(
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            structlog.processors.JSONRenderer(serializer=_orjson_dumps_str),
        ],
        # `ExtraAdder` extracts `extra={...}` fields from the stdlib
        # `LogRecord` and merges them into the structlog event dict
        # BEFORE `JSONRenderer` serializes it. Without this, every
        # `_log.info('msg', extra={'strategy_id': X, ...})` call from
        # a stdlib logger silently drops its `extra` payload — only
        # `event` / `level` / `timestamp` make it to JSON. Pre-fix
        # this affected ~70% of the codebase: every log emit site in
        # `launcher.py`, `trading.py`, `execution_manager.py`,
        # `binance_adapter.py`, `action_submit.py`, `outcome_loop.py`,
        # `outcome_processor.py`, `praxis_outbound.py`, etc. was
        # emitting `{"event": "action rejected by validator"}` with
        # no `strategy_id` / `failed_stage` / `reason_code`. The
        # native structlog API (`_log = structlog.get_logger(...)`,
        # `_log.info('msg', strategy_id=X)`) bypasses the stdlib
        # path entirely so it was unaffected — but only `sequencer.py`
        # and `shutdown_sequencer.py` use that API; everything else
        # in the trade lifecycle uses stdlib `logging.getLogger(...)`.
        foreign_pre_chain=[
            structlog.stdlib.ExtraAdder(),
            *shared_processors,
        ],
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(numeric_level)


def bind_context(**kwargs: Any) -> None:

    '''
    Bind key-value pairs to the asyncio-safe structlog context.

    Args:
        **kwargs (Any): Context fields (epoch_id, account_id, command_id, etc.)

    Returns:
        None
    '''

    structlog.contextvars.bind_contextvars(**kwargs)


def clear_context() -> None:

    '''
    Clear all bound context variables.

    Returns:
        None
    '''

    structlog.contextvars.clear_contextvars()


def get_logger(name: str) -> Any:

    '''
    Return a structlog logger bound to the given name.

    Args:
        name (str): Logger name, typically __name__

    Returns:
        Any: Configured structlog bound logger
    '''

    return structlog.get_logger(name)
