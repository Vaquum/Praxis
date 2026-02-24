'''
Structured logging configuration for Praxis.

Configures structlog with orjson serialization, asyncio-safe context
variable binding, and ISO 8601 UTC timestamps. Call configure_logging()
once at process startup before any other initialization.
'''

import logging

import orjson
import structlog


def configure_logging(log_level: str = 'INFO') -> None:

    '''
    Configure structlog with orjson JSON rendering to stdout.

    Args:
        log_level (str): Minimum log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)

    Returns:
        None
    '''

    numeric_level = getattr(logging, log_level.upper(), logging.INFO)

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
        wrapper_class=structlog.make_filtering_bound_logger(numeric_level),
        logger_factory=structlog.BytesLoggerFactory(),
        cache_logger_on_first_use=True,
    )
