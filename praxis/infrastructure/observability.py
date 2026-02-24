'''
Structured logging configuration for Praxis.

Configures structlog with orjson serialization, asyncio-safe context
variable binding, and ISO 8601 UTC timestamps. Call configure_logging()
once at process startup before any other initialization.
'''

import logging
import sys
from typing import Any

import orjson
import structlog


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
        foreign_pre_chain=shared_processors,
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(numeric_level)
