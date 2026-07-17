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

import asyncio
import dataclasses
import enum
import hashlib
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
    FundTransaction,
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
    OperatorHaltRequested,
    OperatorResumeRequested,
    RegisterAccount,
    TradeClosed,
    TradeOutcomeProduced,
)

__all__ = ['ChainVerificationError', 'EventSpine', 'SpineSchemaError']

_log = logging.getLogger(__name__)

_SCHEMA_VERSION = 3
_CHAIN_VERSION = 1
_HASH_DOMAIN = b'praxis.spine.chain.v1'
_GENESIS_ANCHOR = hashlib.sha256(_HASH_DOMAIN + b'.genesis').hexdigest()
_FRAME_WIDTH = 8

_META_CHAIN_VERSION = 'chain_version'
_META_GENESIS_ANCHOR = 'genesis_anchor'
_META_LEGACY_DEDUP_SYMBOL = 'legacy_dedup_symbol'


class SpineSchemaError(RuntimeError):

    '''Raised when the on-disk schema version is newer than this build supports.'''


class ChainVerificationError(RuntimeError):

    '''Raised when the Event Spine hash chain fails verification.'''


_CREATE_TABLE = '''
CREATE TABLE IF NOT EXISTS events (
    event_seq INTEGER PRIMARY KEY AUTOINCREMENT,
    epoch_id INTEGER NOT NULL,
    timestamp TEXT NOT NULL,
    event_type TEXT NOT NULL,
    payload BLOB NOT NULL,
    prev_hash TEXT,
    hash TEXT
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

_CREATE_FILL_DEDUP_V2 = '''
CREATE TABLE IF NOT EXISTS fill_dedup_v2 (
    epoch_id INTEGER NOT NULL,
    account_id TEXT NOT NULL,
    symbol TEXT NOT NULL,
    dedup_key TEXT NOT NULL,
    UNIQUE(epoch_id, account_id, symbol, dedup_key)
)'''

_CREATE_META = '''
CREATE TABLE IF NOT EXISTS spine_meta (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
)'''

_CREATE_RECONCILE_CURSOR = '''
CREATE TABLE IF NOT EXISTS reconcile_cursor (
    account_id TEXT NOT NULL,
    symbol TEXT NOT NULL,
    last_confirmed_trade_id INTEGER NOT NULL,
    last_confirmed_ts TEXT NOT NULL,
    epoch_id INTEGER NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(account_id, symbol)
)'''

_INSERT = (
    'INSERT INTO events (epoch_id, timestamp, event_type, payload) '
    'VALUES (?, ?, ?, ?)'
)

_UPDATE_HASH = 'UPDATE events SET prev_hash = ?, hash = ? WHERE event_seq = ?'

_TIP_HASH = 'SELECT hash FROM events ORDER BY event_seq DESC LIMIT 1'

_SELECT = (
    'SELECT event_seq, event_type, payload FROM events '
    'WHERE epoch_id = ? AND event_seq > ? ORDER BY event_seq ASC'
)

_SELECT_CHAIN = (
    'SELECT event_seq, epoch_id, timestamp, event_type, payload, prev_hash, hash '
    'FROM events ORDER BY event_seq ASC'
)

_LAST_SEQ = 'SELECT MAX(event_seq) FROM events WHERE epoch_id = ?'

_META_GET = 'SELECT value FROM spine_meta WHERE key = ?'

_META_SET = 'INSERT OR IGNORE INTO spine_meta (key, value) VALUES (?, ?)'

_CURSOR_GET = (
    'SELECT last_confirmed_trade_id FROM reconcile_cursor '
    'WHERE account_id = ? AND symbol = ?'
)

_CURSOR_UPSERT = '''
INSERT INTO reconcile_cursor (
    account_id, symbol, last_confirmed_trade_id, last_confirmed_ts, epoch_id, updated_at
) VALUES (?, ?, ?, ?, ?, ?)
ON CONFLICT(account_id, symbol) DO UPDATE SET
    last_confirmed_trade_id = excluded.last_confirmed_trade_id,
    last_confirmed_ts = excluded.last_confirmed_ts,
    epoch_id = excluded.epoch_id,
    updated_at = excluded.updated_at
'''


_DEDUP_V2_INSERT = (
    'INSERT OR IGNORE INTO fill_dedup_v2 (epoch_id, account_id, symbol, dedup_key) '
    'VALUES (?, ?, ?, ?)'
)

_LEGACY_DEDUP_CHECK = (
    'SELECT 1 FROM fill_dedup WHERE epoch_id = ? AND account_id = ? AND dedup_key = ?'
)

_LEGACY_DEDUP_IDS = 'SELECT epoch_id, account_id, dedup_key FROM fill_dedup'

_FILL_PAYLOAD_SCAN = "SELECT epoch_id, payload FROM events WHERE event_type = 'FillReceived'"

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
        RegisterAccount,
        FundTransaction,
        OperatorHaltRequested,
        OperatorResumeRequested,
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


def _compute_hash(
    prev_hash: str,
    event_seq: int,
    epoch_id: int,
    timestamp: str,
    event_type: str,
    payload: bytes,
) -> str:

    '''
    Compute the SHA-256 chain hash for one event.

    Build a length-framed preimage from the domain marker, chain
    version, predecessor hash, and every stored field so no two distinct
    events can collide through field-boundary ambiguity.

    Args:
        prev_hash (str): Hash of the preceding event, or the genesis anchor.
        event_seq (int): Global sequence number assigned by the insert.
        epoch_id (int): Epoch identifier stored on the row.
        timestamp (str): ISO-8601 timestamp stored on the row.
        event_type (str): Event class name stored on the row.
        payload (bytes): Exact serialized payload stored on the row.

    Returns:
        str: Hex-encoded SHA-256 digest.
    '''

    digest = hashlib.sha256()
    parts = (
        _HASH_DOMAIN,
        str(_CHAIN_VERSION).encode(),
        prev_hash.encode(),
        str(event_seq).encode(),
        str(epoch_id).encode(),
        timestamp.encode(),
        event_type.encode(),
        payload,
    )
    for part in parts:
        digest.update(len(part).to_bytes(_FRAME_WIDTH, 'big'))
        digest.update(part)

    return digest.hexdigest()


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
        self._append_lock = asyncio.Lock()
        self._legacy_dedup_symbol: str | None = None

    async def ensure_schema(self) -> None:

        '''
        Create or migrate the schema to the current version, fail-closed on newer.

        Gate the migration on `PRAGMA user_version`: a database newer
        than this build (`user_version > _SCHEMA_VERSION`) is refused
        rather than silently downgraded; an older or fresh database is
        migrated forward once. The migration is additive (nullable hash
        columns, a metadata table) and idempotent — re-running at the
        current version is a no-op.

        All DDL, the migration, and the version bump run in one
        transaction ended by `commit()`, so a crash mid-migration rolls
        back (the version does not advance) and the next boot re-runs
        the step. The commit also makes the schema durable on the main
        DB file before any caller appends; without it a spine read from
        a separate connection sees an empty file until the first commit.

        Raises:
            SpineSchemaError: If the on-disk schema is newer than supported.

        Returns:
            None
        '''

        version = await self._user_version()
        if version > _SCHEMA_VERSION:
            msg = (
                f'event spine schema version {version} is newer than this '
                f'build supports ({_SCHEMA_VERSION}); refusing to open'
            )
            raise SpineSchemaError(msg)

        try:
            async with self._conn.execute(_CREATE_TABLE):
                pass
            async with self._conn.execute(_CREATE_INDEX):
                pass
            async with self._conn.execute(_CREATE_FILL_DEDUP):
                pass
            async with self._conn.execute(_CREATE_FILL_DEDUP_V2):
                pass
            async with self._conn.execute(_CREATE_META):
                pass
            async with self._conn.execute(_CREATE_RECONCILE_CURSOR):
                pass

            if version < _SCHEMA_VERSION:
                await self._migrate_to_v1()
                await self._migrate_to_v3()
                async with self._conn.execute(f'PRAGMA user_version = {_SCHEMA_VERSION}'):
                    pass

            await self._conn.commit()
        except Exception:
            await self._safe_rollback('event spine schema migration')
            _log.exception('event spine schema migration failed (rollback attempted)')
            raise

        self._legacy_dedup_symbol = await self._get_meta(_META_LEGACY_DEDUP_SYMBOL)
        _log.info('event spine schema ensured', extra={'schema_version': _SCHEMA_VERSION})

    async def _user_version(self) -> int:

        '''
        Return the SQLite `user_version` (0 for a legacy or fresh database).

        Returns:
            int: The stored schema version.
        '''

        async with self._conn.execute('PRAGMA user_version') as cursor:
            row = await cursor.fetchone()

        return int(row[0]) if row else 0

    async def _column_exists(self, table: str, column: str) -> bool:

        '''
        Report whether a column already exists on a table.

        Args:
            table (str): Table name to inspect.
            column (str): Column name to look for.

        Returns:
            bool: True if the column is present.
        '''

        async with self._conn.execute(f'PRAGMA table_info({table})') as cursor:
            rows = await cursor.fetchall()

        return any(row[1] == column for row in rows)

    async def _migrate_to_v1(self) -> None:

        '''
        Add the hash-chain columns to a legacy events table and seed chain metadata.

        The `ALTER TABLE ADD COLUMN` runs only when the columns are
        absent, so a fresh database (created with the columns already)
        skips it. Legacy rows keep NULL hashes and form an unattested
        prefix; no historical hashes are backfilled.

        Returns:
            None
        '''

        if not await self._column_exists('events', 'prev_hash'):
            async with self._conn.execute('ALTER TABLE events ADD COLUMN prev_hash TEXT'):
                pass
        if not await self._column_exists('events', 'hash'):
            async with self._conn.execute('ALTER TABLE events ADD COLUMN hash TEXT'):
                pass

        async with self._conn.execute(_META_SET, (_META_CHAIN_VERSION, str(_CHAIN_VERSION))):
            pass
        async with self._conn.execute(_META_SET, (_META_GENESIS_ANCHOR, _GENESIS_ANCHOR)):
            pass

    async def _migrate_to_v3(self) -> None:

        '''
        Establish the fill-dedup-v2 legacy-symbol boundary, fail-closed on ambiguity.

        New fills dedup on `(epoch, account, symbol, venue_trade_id)` in
        `fill_dedup_v2`. Legacy `fill_dedup` rows carry no symbol, so this
        step proves the historical symbol set by scanning `FillReceived`
        payloads. If the legacy database contains zero or one symbol, that
        proven symbol is recorded and the legacy table is consulted only
        for it (dual-read gating avoids a cross-symbol false-positive). If
        it spans multiple symbols, or a legacy dedup row has no matching
        `FillReceived` event, the migration fails closed — an offline,
        operator-run symbol-aware backfill is required.

        Raises:
            SpineSchemaError: If legacy rows span multiple symbols or a
                legacy dedup row cannot be mapped to a symbol.

        Returns:
            None
        '''

        symbols, fill_keys = await self._scan_fill_dedup_symbols()
        legacy_keys = await self._legacy_dedup_ids()

        unmatched = legacy_keys - fill_keys
        if unmatched:
            msg = (
                f'{len(unmatched)} legacy fill_dedup rows have no matching '
                f'FillReceived event; offline fill_dedup_v2 migration required'
            )
            raise SpineSchemaError(msg)

        if len(symbols) > 1:
            msg = (
                f'legacy database spans {len(symbols)} symbols; offline '
                f'symbol-aware fill_dedup_v2 backfill required'
            )
            raise SpineSchemaError(msg)

        legacy_symbol = next(iter(symbols)) if symbols else ''
        async with self._conn.execute(_META_SET, (_META_LEGACY_DEDUP_SYMBOL, legacy_symbol)):
            pass

    async def _scan_fill_dedup_symbols(self) -> tuple[set[str], set[tuple[int, str, str]]]:

        '''
        Scan FillReceived events for their symbols and composite dedup keys.

        Returns:
            tuple[set[str], set[tuple[int, str, str]]]: The distinct symbols
            and the set of `(epoch_id, account_id, venue_trade_id)` identities
            seen across all FillReceived events. The composite key mirrors the
            legacy `fill_dedup` uniqueness so orphan detection cannot be fooled
            by a venue_trade_id shared across accounts or epochs.
        '''

        msg = (
            'legacy FillReceived payload is malformed (undecodable, missing, or '
            'non-string symbol/account_id/venue_trade_id); offline repair '
            'required before migration'
        )
        symbols: set[str] = set()
        fill_keys: set[tuple[int, str, str]] = set()
        async with self._conn.execute(_FILL_PAYLOAD_SCAN) as cursor:
            async for epoch_id, payload in cursor:
                try:
                    record = orjson.loads(payload)
                    symbol = record['symbol']
                    account_id = record['account_id']
                    venue_trade_id = record['venue_trade_id']
                except (orjson.JSONDecodeError, KeyError, TypeError) as exc:
                    raise SpineSchemaError(msg) from exc

                if not (
                    isinstance(symbol, str)
                    and isinstance(account_id, str)
                    and isinstance(venue_trade_id, str)
                ):
                    raise SpineSchemaError(msg)

                symbols.add(symbol)
                fill_keys.add((epoch_id, account_id, venue_trade_id))

        return symbols, fill_keys

    async def _legacy_dedup_ids(self) -> set[tuple[int, str, str]]:

        '''
        Return the composite dedup identities in the legacy fill_dedup table.

        Returns:
            set[tuple[int, str, str]]: The legacy `(epoch_id, account_id,
            dedup_key)` identities, matching the table's uniqueness constraint.
        '''

        async with self._conn.execute(_LEGACY_DEDUP_IDS) as cursor:
            return {(row[0], row[1], row[2]) async for row in cursor}

    async def _get_meta(self, key: str) -> str | None:

        '''
        Return a spine_meta value, or None if the key is absent.

        Args:
            key (str): Metadata key.

        Returns:
            str | None: The stored value, or None.
        '''

        async with self._conn.execute(_META_GET, (key,)) as cursor:
            row = await cursor.fetchone()

        return str(row[0]) if row is not None else None

    async def _is_legacy_duplicate(self, epoch_id: int, event: FillReceived) -> bool:

        '''
        Report whether a fill was already recorded under the legacy dedup key.

        Consulted only for the proven legacy symbol, so a same-id fill on a
        different symbol never matches a legacy row.

        Args:
            epoch_id (int): Current epoch identifier.
            event (FillReceived): The fill being appended.

        Returns:
            bool: True if the legacy table already holds this trade id.
        '''

        if not self._legacy_dedup_symbol or event.symbol != self._legacy_dedup_symbol:
            return False

        async with self._conn.execute(
            _LEGACY_DEDUP_CHECK, (epoch_id, event.account_id, event.venue_trade_id)
        ) as cursor:
            return await cursor.fetchone() is not None

    async def _genesis_anchor(self) -> str:

        '''
        Return the stored genesis anchor, falling back to the build constant.

        Returns:
            str: The predecessor hash for the first hashed event.
        '''

        async with self._conn.execute(_META_GET, (_META_GENESIS_ANCHOR,)) as cursor:
            row = await cursor.fetchone()

        return str(row[0]) if row and row[0] is not None else _GENESIS_ANCHOR

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

    async def _commit(self, context: str) -> None:

        '''
        Commit the pending transaction, rolling back on commit failure.

        A failed `commit()` can leave the connection in an open
        transaction that would corrupt later writes. On failure this
        rolls back best-effort, logs, and re-raises the commit exception
        so the caller sees the root cause.

        Args:
            context (str): Short tag for the log line so the operator
                can tell which commit path failed.
        '''

        try:
            await self._conn.commit()
        except Exception:
            await self._safe_rollback(context)
            _log.exception('event spine commit failed during %s', context)
            raise

    async def append(self, event: Event, epoch_id: int) -> int | None:

        '''
        Serialize, hash-chain, and append a domain event under the append lock.

        Hold `self._append_lock` across the whole critical section — tip
        read, insert, hash update, and commit — so two concurrent
        `append` coroutines sharing the one connection cannot interleave
        at an `await` and fork the chain (both reading the same tip and
        writing sibling rows with the same `prev_hash`).

        Args:
            event (Event): Domain event dataclass to persist
            epoch_id (int): Current epoch identifier

        Returns:
            int | None: Assigned event_seq, or None if duplicate fill dropped
        '''

        async with self._append_lock:
            return await self._append_locked(event, epoch_id)

    async def _append_locked(self, event: Event, epoch_id: int) -> int | None:

        '''
        Serialize and append a domain event to the log.

        Deduplicate FillReceived events by (account_id, symbol,
        venue_trade_id) within the epoch via `fill_dedup_v2`, plus a
        dual-read of the legacy `fill_dedup` table for the one proven
        pre-migration symbol. Duplicate fills are silently dropped per RFC.
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
                is_duplicate = await self._is_legacy_duplicate(epoch_id, event)
                if not is_duplicate:
                    async with self._conn.execute(
                        _DEDUP_V2_INSERT,
                        (epoch_id, event.account_id, event.symbol, event.venue_trade_id),
                    ) as cursor:
                        is_duplicate = cursor.rowcount == 0
                seq = None if is_duplicate else await self._append_event(event, epoch_id)
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
        await self._commit('event spine append')
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
        Serialize, insert, and hash-chain an event into the events table.

        Read the current chain tip, insert the row, then update it with
        the predecessor hash and this row's SHA-256 chain hash. The tip
        read and both writes run inside the caller's transaction and
        under the append lock, so the `prev_hash` committed here is the
        hash of the immediately preceding event (or the genesis anchor
        for the first hashed row after a legacy prefix).

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
        prev_hash = await self._current_tip_hash()
        async with self._conn.execute(
            _INSERT, (epoch_id, timestamp, event_type, payload)
        ) as cursor:
            if cursor.lastrowid is None:
                msg = 'cursor.lastrowid was None after INSERT'
                raise RuntimeError(msg)
            event_seq = cursor.lastrowid
        row_hash = _compute_hash(
            prev_hash, event_seq, epoch_id, timestamp, event_type, payload,
        )
        async with self._conn.execute(_UPDATE_HASH, (prev_hash, row_hash, event_seq)):
            pass

        return event_seq

    async def _current_tip_hash(self) -> str:

        '''
        Return the hash of the current chain tip, or the genesis anchor.

        The tip is the row with the highest `event_seq`. A missing row
        (empty spine) or a NULL-hash tip (the spine still ends in the
        legacy prefix) both anchor the next hash to the genesis marker.

        Returns:
            str: The predecessor hash for the next appended event.
        '''

        async with self._conn.execute(_TIP_HASH) as cursor:
            row = await cursor.fetchone()

        if row is None or row[0] is None:
            return await self._genesis_anchor()

        return str(row[0])

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

    async def verify_chain(self) -> None:

        '''
        Verify the global hash chain over every event ordered by event_seq.

        Accept an empty spine and a leading prefix of NULL-hash legacy
        rows. From the first hashed row onward, require that each row's
        `prev_hash` equals the preceding hashed row's `hash` (the genesis
        anchor for the first), and that recomputing the hash over the
        stored fields reproduces the stored `hash`. A hashed-to-unhashed
        transition, broken linkage (a deleted or reordered row), or an
        altered field fails closed.

        Raises:
            ChainVerificationError: If the chain is broken or tampered.

        Returns:
            None
        '''

        expected_prev = await self._genesis_anchor()
        in_legacy_prefix = True

        row_count = 0
        async with self._conn.execute(_SELECT_CHAIN) as cursor:
            async for row in cursor:
                event_seq, epoch_id, timestamp, event_type, payload, prev_hash, row_hash = row
                row_count += 1
                if row_hash is None:
                    if not in_legacy_prefix:
                        msg = (
                            f'event spine chain broken: unhashed row at '
                            f'event_seq={event_seq} follows a hashed row'
                        )
                        raise ChainVerificationError(msg)
                    continue

                in_legacy_prefix = False
                if prev_hash != expected_prev:
                    msg = (
                        f'event spine chain broken: event_seq={event_seq} '
                        f'prev_hash does not link to the preceding event'
                    )
                    raise ChainVerificationError(msg)

                recomputed = _compute_hash(
                    prev_hash, event_seq, epoch_id, timestamp, event_type, payload,
                )
                if recomputed != row_hash:
                    msg = (
                        f'event spine chain tampered: event_seq={event_seq} '
                        f'hash does not match its stored fields'
                    )
                    raise ChainVerificationError(msg)

                expected_prev = row_hash

        _log.info('event spine chain verified', extra={'rows': row_count})

    async def get_reconcile_cursor(self, account_id: str, symbol: str) -> int | None:

        '''
        Return the last REST-confirmed trade id for an (account, symbol).

        The cursor is keyed by account and symbol across epochs — Binance
        trade ids outlive Praxis epochs — so a restart or epoch bump
        resumes backfill from the last confirmed id rather than a
        bootstrap lookback.

        Args:
            account_id (str): Account identifier.
            symbol (str): Trading pair symbol.

        Returns:
            int | None: The last confirmed trade id, or None if unset.
        '''

        async with self._conn.execute(_CURSOR_GET, (account_id, symbol)) as cursor:
            row = await cursor.fetchone()

        return int(row[0]) if row is not None else None

    async def set_reconcile_cursor(
        self,
        account_id: str,
        symbol: str,
        *,
        last_confirmed_trade_id: int,
        last_confirmed_ts: str,
        epoch_id: int,
        updated_at: str,
    ) -> None:

        '''
        Upsert the REST-confirmed backfill cursor for an (account, symbol).

        Only a fully processed REST page advances the cursor; WS
        observations never do. `epoch_id` is stored as metadata only —
        the cursor is cross-epoch.

        Args:
            account_id (str): Account identifier.
            symbol (str): Trading pair symbol.
            last_confirmed_trade_id (int): Highest trade id from a fully
                processed REST page.
            last_confirmed_ts (str): ISO-8601 timestamp of that trade.
            epoch_id (int): Epoch that last advanced the cursor (metadata).
            updated_at (str): ISO-8601 write time.

        Returns:
            None
        '''

        async with self._append_lock:
            async with self._conn.execute(
                _CURSOR_UPSERT,
                (
                    account_id,
                    symbol,
                    last_confirmed_trade_id,
                    last_confirmed_ts,
                    epoch_id,
                    updated_at,
                ),
            ):
                pass
            await self._commit('reconcile cursor upsert')
