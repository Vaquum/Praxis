'''
Append-only event log backed by SQLite.

Provide durable, monotonically sequenced storage for domain events.
Caller owns the `aiosqlite` connection's lifecycle (open/close);
`EventSpine` owns the transaction boundaries internally — every
successful `append()` calls `commit()` before returning, so the
returned `seq` means "this event is on disk and visible to other
connections". The pre-fix design (caller owns transaction boundaries
spanning event append, projection update, and outbox insertion) was
never actually exercised by any caller, and silently relied on
implicit-transaction-without-commit behaviour to lose every spine
write across container recreate. Per-event commit is the correct
contract for an append-only log on the order critical path.
'''

from __future__ import annotations

import dataclasses
import enum
import logging
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
    MarkSampled,
    OrderAcked,
    OrderCanceled,
    OrderExpired,
    OrderQuoteNativeFilled,
    OrderRejected,
    OrderSubmitFailed,
    OrderSubmitIntent,
    OrderSubmitted,
    OutcomeAcked,
    OutcomeDeliveryContextRecorded,
    OutcomeReplayAbandoned,
    TradeClosed,
    TradeOutcomeProduced,
)

__all__ = ['EventSpine']

_log = logging.getLogger(__name__)

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
        OrderQuoteNativeFilled,
        OrderAcked,
        FillReceived,
        OrderRejected,
        OrderCanceled,
        OrderExpired,
        TradeClosed,
        TradeOutcomeProduced,
        OutcomeAcked,
        OutcomeDeliveryContextRecorded,
        OutcomeReplayAbandoned,
        MarkSampled,
    )
}

_TYPE_HINTS: dict[str, dict[str, Any]] = {
    name: get_type_hints(cls) for name, cls in _EVENT_REGISTRY.items()
}

_NESTED_TYPE_HINTS: dict[type, dict[str, Any]] = {}


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

    result = value
    if target is Decimal:
        result = Decimal(str(value))
    elif target is datetime:
        result = datetime.fromisoformat(str(value))
    elif isinstance(target, type) and issubclass(target, enum.Enum):
        result = target(value)
    elif dataclasses.is_dataclass(target) and isinstance(value, dict):
        if target not in _NESTED_TYPE_HINTS:
            _NESTED_TYPE_HINTS[target] = get_type_hints(target)
        hints = _NESTED_TYPE_HINTS[target]
        coerced = {k: _coerce(v, hints[k]) for k, v in value.items() if k in hints}
        result = target(**coerced)

    return result


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
    hints = _TYPE_HINTS[event_type]
    coerced = {k: _coerce(v, hints[k]) for k, v in raw.items() if k in hints}
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

        Calls `commit()` after the DDL so the schema is durable on the
        main DB file (not just the rollback journal) before any caller
        starts appending. Without this, every spine read from a
        separate connection sees an empty file until the first
        successful commit elsewhere.

        Returns:
            None
        '''

        async with self._conn.execute(_CREATE_TABLE):
            pass
        async with self._conn.execute(_CREATE_INDEX):
            pass
        async with self._conn.execute(_CREATE_FILL_DEDUP):
            pass
        await self._conn.commit()
        _log.info('event spine schema ensured')

    async def _safe_rollback(self, context: str) -> None:

        '''
        Best-effort rollback that logs but does not raise.

        Used in `append()`'s exception handlers so a rollback failure
        cannot mask the original DML / commit exception that the
        caller actually needs to see.

        Args:
            context (str): Short tag for the log line so the operator
                can tell which failure path triggered the rollback.
        '''

        try:
            await self._conn.rollback()
        except Exception:  # noqa: BLE001 - rollback failure is logged, not raised
            _log.exception('event spine rollback failed during %s', context)

    async def append(self, event: Event, epoch_id: int) -> int | None:

        '''
        Serialize and append a domain event to the log.

        Deduplicate FillReceived events by (account_id, venue_trade_id)
        within the epoch. Duplicate fills are silently dropped per RFC.
        FillReceived atomicity is guaranteed internally: both the
        dedup insert and the event insert run in a single implicit
        transaction (Python sqlite3 auto-begins on the first DML
        statement), then `commit()` or `rollback()` ends it. Either
        both inserts are durable together, or neither is. The
        implementation comment below `if isinstance(event,
        FillReceived):` carries the historical context for why
        this is no longer SAVEPOINT-based.

        Calls `await self._conn.commit()` after every successful insert
        so each event is durable on the main DB file before this method
        returns. Without the commit, `aiosqlite`'s default
        implicit-transaction mode (`isolation_level=""`) leaves writes
        in the rollback journal, invisible to any other connection and
        rolled back on connection close without explicit `commit()` and on crash/unclean shutdown — observed in production
        where the spine file's main DB stayed empty for days while the
        journal grew, and every container recreate wiped 24+ hours of
        spine data. Commit-per-append is the minimal correct fix:
        per-event durability matches the at-least-once log semantics
        the caller already assumes (every `await append(...)` returning
        a `seq` means "this event is on disk"), and the per-event
        `fsync` cost is negligible compared to the venue REST round
        trip on the same critical path.

        Args:
            event (Event): Domain event dataclass to persist
            epoch_id (int): Current epoch identifier

        Returns:
            int | None: Assigned event_seq, or None if duplicate fill dropped
        '''

        if isinstance(event, FillReceived):
            # Atomicity for the dedup-insert + event-insert pair via
            # Python sqlite3's implicit BEGIN-on-DML: the first INSERT
            # auto-begins a transaction, the second INSERT runs in the
            # same transaction, and `commit()` / `rollback()` end it.
            # Both inserts are durable together or neither is.
            #
            # Pre-fix this used SAVEPOINT/RELEASE/ROLLBACK TO. That
            # path interacted poorly with Python sqlite3's default
            # `isolation_level=""` semantics: non-DML statements
            # (SAVEPOINT, RELEASE, ROLLBACK TO) trigger an implicit
            # COMMIT before they run, collapsing the savepoint stack.
            # By the time RELEASE ran in production the savepoint had
            # been committed away and sqlite raised
            # `OperationalError: no such savepoint: fill_atomic`.
            # The implicit BEGIN-on-DML path used here sidesteps the
            # SAVEPOINT API entirely.
            # Two separate try blocks so a commit failure doesn't
            # get caught by the DML-failure handler. Pre-fix a single
            # try/except wrapped both; on commit failure the except's
            # rollback would run AND a rollback failure inside that
            # except would mask the original commit exception. Now:
            #   - DML failure: rollback best-effort, re-raise the DML
            #     exception
            #   - commit failure: rollback best-effort, re-raise the
            #     COMMIT exception (preserves the root cause)
            try:
                async with self._conn.execute(
                    _DEDUP_INSERT, (epoch_id, event.account_id, event.venue_trade_id)
                ) as cursor:
                    rowcount = cursor.rowcount
                if rowcount == 0:
                    seq = None
                else:
                    seq = await self._append_event(event, epoch_id)
            except Exception:
                await self._safe_rollback('event spine fill-atomic DML failure')
                _log.exception(
                    'event spine fill-atomic DML failed (rollback attempted)',
                    extra={
                        'epoch_id': epoch_id,
                        'account_id': event.account_id,
                        'venue_trade_id': event.venue_trade_id,
                        'venue_order_id': event.venue_order_id,
                    },
                )
                raise
            try:
                await self._conn.commit()
            except Exception:
                await self._safe_rollback('event spine fill-atomic commit failure')
                _log.exception(
                    'event spine fill-atomic commit failed',
                    extra={
                        'epoch_id': epoch_id,
                        'account_id': event.account_id,
                        'venue_trade_id': event.venue_trade_id,
                        'venue_order_id': event.venue_order_id,
                    },
                )
                raise
            if seq is None:
                _log.warning(
                    'event spine fill deduplicated',
                    extra={
                        'epoch_id': epoch_id,
                        'account_id': event.account_id,
                        'venue_trade_id': event.venue_trade_id,
                        'venue_order_id': event.venue_order_id,
                    },
                )
            else:
                _log.debug(
                    'event spine appended',
                    extra={
                        'epoch_id': epoch_id,
                        'event_type': type(event).__name__,
                        'event_seq': seq,
                        'account_id': event.account_id,
                    },
                )
            return seq

        seq = await self._append_event(event, epoch_id)
        await self._conn.commit()
        _log.debug(
            'event spine appended',
            extra={
                'epoch_id': epoch_id,
                'event_type': type(event).__name__,
                'event_seq': seq,
                'account_id': event.account_id,
            },
        )
        return seq

    async def _append_event(self, event: Event, epoch_id: int) -> int:

        '''
        Serialize and insert event into the events table.

        Args:
            event (Event): Domain event dataclass to persist
            epoch_id (int): Current epoch identifier

        Returns:
            int: Assigned event_seq
        '''

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
