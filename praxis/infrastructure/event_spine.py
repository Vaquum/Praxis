'''
Append-only event log backed by SQLite.

Provide durable, monotonically sequenced storage for domain events.
Caller owns the aiosqlite connection and transaction boundaries,
enabling atomic writes spanning event append, projection update,
and outbox insertion.
'''

from __future__ import annotations

import dataclasses
import enum
import types
from datetime import datetime
from decimal import Decimal
from typing import Any, Union, get_args, get_origin, get_type_hints

import aiosqlite
import orjson

from praxis.core.domain.events import (
    CommandAccepted,
    Event,
    FillReceived,
    OrderAcked,
    OrderCanceled,
    OrderExpired,
    OrderRejected,
    OrderSubmitFailed,
    OrderSubmitIntent,
    OrderSubmitted,
    TradeClosed,
)

__all__ = ['EventSpine']

_CREATE_TABLE = '''
CREATE TABLE IF NOT EXISTS events (
    event_seq INTEGER PRIMARY KEY AUTOINCREMENT,
    epoch_id INTEGER NOT NULL,
    timestamp TEXT NOT NULL,
    event_type TEXT NOT NULL,
    payload BLOB NOT NULL
)'''

_CREATE_INDEX = (
    'CREATE INDEX IF NOT EXISTS ix_events_epoch_seq '
    'ON events (epoch_id, event_seq)'
)

_CREATE_FILL_DEDUP = '''
CREATE TABLE IF NOT EXISTS fill_dedup (
    epoch_id INTEGER NOT NULL,
    account_id TEXT NOT NULL,
    dedup_key TEXT NOT NULL,
    UNIQUE(epoch_id, account_id, dedup_key)
)'''

_INSERT = (
    'INSERT INTO events (epoch_id, timestamp, event_type, payload) '
    'VALUES (?, ?, ?, ?)'
)

_SELECT = (
    'SELECT event_seq, event_type, payload FROM events '
    'WHERE epoch_id = ? AND event_seq > ? ORDER BY event_seq ASC'
)

_LAST_SEQ = 'SELECT MAX(event_seq) FROM events WHERE epoch_id = ?'


_DEDUP_INSERT = (
    'INSERT OR IGNORE INTO fill_dedup (epoch_id, account_id, dedup_key) '
    'VALUES (?, ?, ?)'
)

_EVENT_REGISTRY: dict[str, type] = {
    cls.__name__: cls
    for cls in (
        CommandAccepted,
        OrderSubmitIntent,
        OrderSubmitted,
        OrderSubmitFailed,
        OrderAcked,
        FillReceived,
        OrderRejected,
        OrderCanceled,
        OrderExpired,
        TradeClosed,
    )
}


def _serialize_default(obj: Any) -> Any:

    '''
    Serialize Decimal to string for orjson.

    Args:
        obj (Any): Object that orjson cannot serialize natively

    Returns:
        Any: JSON-serializable representation
    '''

    if isinstance(obj, Decimal):
        return str(obj)
    msg = f"Object of type {type(obj).__name__} is not JSON serializable"
    raise TypeError(msg)


def _coerce(value: Any, target: type) -> Any:

    '''
    Coerce a deserialized JSON value to the expected Python type.

    Args:
        value (Any): Raw value from orjson.loads
        target (type): Expected Python type from dataclass field annotation

    Returns:
        Any: Value coerced to the target type
    '''

    if value is None:
        return None

    origin = get_origin(target)
    if origin is Union or origin is types.UnionType:
        args = [a for a in get_args(target) if a is not type(None)]
        return _coerce(value, args[0]) if args else value

    if target is Decimal:
        return Decimal(str(value))

    if target is datetime:
        return datetime.fromisoformat(str(value))

    if isinstance(target, type) and issubclass(target, enum.Enum):
        return target(value)

    return value


def _hydrate(event_type: str, payload: bytes) -> Event:

    '''
    Reconstruct a domain Event from its serialized payload.

    Args:
        event_type (str): Event class name from the registry
        payload (bytes): orjson-serialized event data

    Returns:
        Event: Hydrated domain event dataclass
    '''

    cls = _EVENT_REGISTRY.get(event_type)
    if cls is None:
        msg = f"Unknown event_type: {event_type!r}"
        raise ValueError(msg)
    raw: dict[str, Any] = orjson.loads(payload)
    hints = get_type_hints(cls)
    coerced = {k: _coerce(v, hints[k]) for k, v in raw.items()}
    return cls(**coerced)  # type: ignore[no-any-return]


class EventSpine:

    '''
    Provide append-only event log backed by a single SQLite table.

    Args:
        conn (aiosqlite.Connection): Caller-owned database connection
    '''

    def __init__(self, conn: aiosqlite.Connection) -> None:

        '''
        Store the caller-owned connection.

        Args:
            conn (aiosqlite.Connection): Caller-owned database connection
        '''

        self._conn = conn

    async def ensure_schema(self) -> None:

        '''
        Create the events table, epoch index, and fill dedup table if they do not exist.

        Returns:
            None
        '''

        async with self._conn.execute(_CREATE_TABLE):
            pass
        async with self._conn.execute(_CREATE_INDEX):
            pass
        async with self._conn.execute(_CREATE_FILL_DEDUP):
            pass

    async def append(self, event: Event, epoch_id: int) -> int | None:

        '''
        Serialize and append a domain event to the log.

        Deduplicate FillReceived events by (account_id, venue_trade_id)
        within the epoch. Duplicate fills are silently dropped per RFC.

        Args:
            event (Event): Domain event dataclass to persist
            epoch_id (int): Current epoch identifier

        Returns:
            int | None: Assigned event_seq, or None if duplicate fill dropped
        '''

        if isinstance(event, FillReceived):
            cursor = await self._conn.execute(
                _DEDUP_INSERT, (epoch_id, event.account_id, event.venue_trade_id)
            )
            if cursor.rowcount == 0:
                return None

        event_type = type(event).__name__
        if event_type not in _EVENT_REGISTRY:
            msg = f'Unregistered event type "{event_type}" cannot be appended'
            raise ValueError(msg)
        timestamp = event.timestamp.isoformat()
        payload = orjson.dumps(dataclasses.asdict(event), default=_serialize_default)
        async with self._conn.execute(
            _INSERT, (epoch_id, timestamp, event_type, payload)
        ) as cursor:
            if cursor.lastrowid is None:
                msg = 'cursor.lastrowid was None after INSERT'
                raise RuntimeError(msg)
            return cursor.lastrowid

    async def read(self, epoch_id: int, after_seq: int = 0) -> list[tuple[int, Event]]:

        '''
        Read events for an epoch, optionally after a sequence number.

        Args:
            epoch_id (int): Epoch to read events from
            after_seq (int): Return events with sequence numbers greater than this

        Returns:
            list[tuple[int, Event]]: Pairs of (event_seq, hydrated Event)
        '''

        async with self._conn.execute(_SELECT, (epoch_id, after_seq)) as cursor:
            rows = await cursor.fetchall()
        return [(row[0], _hydrate(row[1], row[2])) for row in rows]

    async def last_event_seq(self, epoch_id: int) -> int | None:

        '''
        Return the highest event sequence number for an epoch.

        Args:
            epoch_id (int): Epoch to query

        Returns:
            int | None: Highest event_seq, or None if epoch has no events
        '''

        async with self._conn.execute(_LAST_SEQ, (epoch_id,)) as cursor:
            row = await cursor.fetchone()
        return row[0] if row else None
