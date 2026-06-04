'''Mirror Praxis event_spine.sqlite into ClickHouse on a polling cadence.'''

from __future__ import annotations

import logging
import os
import re
import sqlite3
import sys
import time
from datetime import UTC, datetime
from typing import Final

import clickhouse_connect
from clickhouse_connect.driver.exceptions import DatabaseError, OperationalError


_IDENTIFIER_RE: Final = re.compile(r'^[A-Za-z_][A-Za-z0-9_]*$')


_log: Final = logging.getLogger(__name__)

_BACKOFF_BASE_S: Final = 1.0
_BACKOFF_MAX_S: Final = 300.0
_RECOVERABLE_ERRORS: Final = (
    sqlite3.Error,
    OSError,
    DatabaseError,
    OperationalError,
)

_SCHEMA_SQL_TEMPLATE = '''
CREATE TABLE IF NOT EXISTS {database}.events (
    event_seq UInt64,
    epoch_id UInt32,
    ts DateTime64(6, 'UTC'),
    event_type LowCardinality(String),
    payload String,
    strategy_id LowCardinality(String) MATERIALIZED JSONExtractString(payload, 'strategy_id'),
    command_id String MATERIALIZED JSONExtractString(payload, 'command_id'),
    trade_id String MATERIALIZED JSONExtractString(payload, 'trade_id'),
    symbol LowCardinality(String) MATERIALIZED JSONExtractString(payload, 'symbol'),
    side LowCardinality(String) MATERIALIZED JSONExtractString(payload, 'side'),
    account_id LowCardinality(String) MATERIALIZED JSONExtractString(payload, 'account_id'),
    status LowCardinality(String) MATERIALIZED JSONExtractString(payload, 'status'),
    reason String MATERIALIZED JSONExtractString(payload, 'reason'),
    qty Nullable(Decimal(38, 18)) MATERIALIZED toDecimal128OrNull(JSONExtractString(payload, 'qty'), 18),
    price Nullable(Decimal(38, 18)) MATERIALIZED toDecimal128OrNull(JSONExtractString(payload, 'price'), 18),
    fee Nullable(Decimal(38, 18)) MATERIALIZED toDecimal128OrNull(JSONExtractString(payload, 'fee'), 18)
)
ENGINE = ReplacingMergeTree(event_seq)
PARTITION BY epoch_id
ORDER BY (epoch_id, event_seq)
'''


def _parse_ts(raw: str) -> datetime:

    '''
    Parse the spine's `timestamp` column into a UTC-aware datetime.

    The Praxis spine writes `event.timestamp.isoformat()` from a
    tz-aware `_EventBase.timestamp` field. The spine's validator
    enforces tz-awareness but not UTC, so any offset can land on
    disk; this parser preserves the instant via `astimezone(UTC)`
    when an offset is present and falls back to `replace(tzinfo=UTC)`
    only for the truly-naive case. A trailing `Z` is normalized to
    `+00:00` defensively so external producers that emit Zulu suffix
    parse the same.

    Args:
        raw (str): ISO-8601 timestamp string from the spine.

    Returns:
        datetime: tz-aware datetime anchored to UTC.
    '''

    normalized = raw[:-1] + '+00:00' if raw.endswith('Z') else raw
    parsed = datetime.fromisoformat(normalized)

    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)

    return parsed.astimezone(UTC)


def _ensure_schema(ch: clickhouse_connect.driver.Client, database: str) -> None:

    '''
    Create the target database and the `events` table if missing.

    Idempotent (both statements use `IF NOT EXISTS`); safe to call on
    every cold start and after every transient ClickHouse recovery.

    Args:
        ch (clickhouse_connect.driver.Client): Connected ClickHouse
            client.
        database (str): Target database name. Caller must have
            validated this against `_IDENTIFIER_RE` before reaching
            here; the value is interpolated into SQL identifiers.
    '''

    ch.command(f'CREATE DATABASE IF NOT EXISTS {database}')
    ch.command(_SCHEMA_SQL_TEMPLATE.format(database=database))


def _current_cursor(ch: clickhouse_connect.driver.Client, database: str) -> int:

    '''
    Read the high-water mark `event_seq` from the target table.

    Returns `0` on an empty table or a NULL aggregate, which lets
    the next batch insert from the start of the spine without a
    separate cursor file.

    Args:
        ch (clickhouse_connect.driver.Client): Connected ClickHouse
            client.
        database (str): Target database name.

    Returns:
        int: Highest `event_seq` currently mirrored, or `0` if none.
    '''

    result = ch.query(f'SELECT max(event_seq) FROM {database}.events').result_rows

    if not result or result[0][0] is None:
        return 0

    return int(result[0][0])


def _fetch_batch(spine_path: str, cursor: int, batch_size: int) -> list[tuple]:

    '''
    Pull a batch of events from the spine SQLite above `cursor`.

    Opens the spine read-only via SQLite's URI form and pins
    `PRAGMA query_only=ON` for defense-in-depth so a programming
    error cannot write to the live spine. Ordered by `event_seq` to
    preserve append-order semantics across batches.

    Args:
        spine_path (str): Absolute filesystem path to the spine
            SQLite database.
        cursor (int): Exclusive lower bound on `event_seq` —
            returned rows satisfy `event_seq > cursor`.
        batch_size (int): Hard upper bound on the row count for
            this batch.

    Returns:
        list[tuple]: Rows of `(event_seq, epoch_id, timestamp,
            event_type, payload)`.
    '''

    with sqlite3.connect(f'file:{spine_path}?mode=ro', uri=True) as conn:
        conn.execute('PRAGMA query_only=ON')
        return conn.execute(
            'SELECT event_seq, epoch_id, timestamp, event_type, payload '
            'FROM events WHERE event_seq > ? ORDER BY event_seq LIMIT ?',
            (cursor, batch_size),
        ).fetchall()


def _to_rows(raw_rows: list[tuple]) -> list[list]:

    '''
    Transform spine rows into ClickHouse-insert rows.

    Decodes any `bytes` payloads to UTF-8 with replacement-on-error
    (so a single bad byte cannot block the whole batch), parses the
    timestamp via `_parse_ts`, and coerces the integer columns to
    `int` (SQLite may return them as `int` or `int`-like objects).

    Args:
        raw_rows (list[tuple]): Output of `_fetch_batch`.

    Returns:
        list[list]: Rows in the column order
            `(event_seq, epoch_id, ts, event_type, payload)`,
            ready for `ch.insert`.
    '''

    out = []

    for seq, epoch, ts, event_type, raw_payload in raw_rows:
        decoded_payload = (
            raw_payload.decode('utf-8', errors='replace')
            if isinstance(raw_payload, bytes)
            else raw_payload
        )

        out.append([
            int(seq),
            int(epoch),
            _parse_ts(ts),
            event_type,
            decoded_payload,
        ])

    return out


def _backoff_seconds(consecutive_failures: int) -> float:

    '''
    Compute the next sleep interval given a consecutive-failure run.

    Doubles from `_BACKOFF_BASE_S=1.0s` on each consecutive failure
    and clamps at `_BACKOFF_MAX_S=300s`. Callers always pass
    `consecutive_failures >= 1` (the call site increments before
    invoking); a `<= 0` input would yield a sub-base sleep, which
    is structurally unreachable here.

    Args:
        consecutive_failures (int): Number of consecutive failed
            ticks, starting at `1` for the first failure.

    Returns:
        float: Sleep duration in seconds.
    '''

    return min(_BACKOFF_BASE_S * (2 ** (consecutive_failures - 1)), _BACKOFF_MAX_S)


def main() -> None:

    '''
    Run the spine-mirror polling loop.

    Reads required env vars (`SPINE_PATH`, `CLICKHOUSE_HOST`,
    `CLICKHOUSE_USER`, `CLICKHOUSE_PASSWORD`) and optional ones
    (`CLICKHOUSE_PORT=8123`, `CLICKHOUSE_DATABASE=praxis`,
    `SYNC_INTERVAL_SECONDS=5`, `BATCH_SIZE=10000`); validates
    `CLICKHOUSE_DATABASE` against `_IDENTIFIER_RE` to prevent SQL
    injection through identifier interpolation. The polling loop
    lazily constructs the ClickHouse client and ensures the schema
    on the first iteration; both are gated by flags so a cold-start
    race against ClickHouse boot flows through the
    `_RECOVERABLE_ERRORS` retry envelope with exponential backoff
    rather than crashing the process.

    Raises:
        KeyError: A required env var is missing.
        ValueError: `CLICKHOUSE_DATABASE` is not a safe SQL
            identifier.
    '''


    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s %(levelname)s %(name)s %(message)s',
        stream=sys.stderr,
    )

    spine_path = os.environ['SPINE_PATH']
    ch_host = os.environ['CLICKHOUSE_HOST']
    ch_port = int(os.environ.get('CLICKHOUSE_PORT', '8123'))
    ch_database = os.environ.get('CLICKHOUSE_DATABASE', 'praxis')
    ch_user = os.environ['CLICKHOUSE_USER']
    ch_password = os.environ['CLICKHOUSE_PASSWORD']
    sync_interval_s = float(os.environ.get('SYNC_INTERVAL_SECONDS', '5'))
    batch_size = int(os.environ.get('BATCH_SIZE', '10000'))

    if not _IDENTIFIER_RE.fullmatch(ch_database):
        msg = (
            f'CLICKHOUSE_DATABASE={ch_database!r} is not a safe identifier; '
            f'must match {_IDENTIFIER_RE.pattern}'
        )
        raise ValueError(msg)

    _log.info(
        'spine-mirror starting: spine=%s clickhouse=%s:%d/%s interval=%.1fs batch=%d',
        spine_path, ch_host, ch_port, ch_database, sync_interval_s, batch_size,
    )

    ch: clickhouse_connect.driver.Client | None = None
    schema_ready = False
    consecutive_failures = 0

    while True:
        try:
            if ch is None:
                ch = clickhouse_connect.get_client(
                    host=ch_host,
                    port=ch_port,
                    database=ch_database,
                    username=ch_user,
                    password=ch_password,
                )

            if not schema_ready:
                _ensure_schema(ch, ch_database)
                schema_ready = True

            cursor = _current_cursor(ch, ch_database)
            raw_rows = _fetch_batch(spine_path, cursor, batch_size)

            if raw_rows:
                rows = _to_rows(raw_rows)
                ch.insert(
                    f'{ch_database}.events',
                    rows,
                    column_names=['event_seq', 'epoch_id', 'ts', 'event_type', 'payload'],
                )
                last_seq = rows[-1][0]
                _log.info('synced %d rows; cursor %d -> %d', len(rows), cursor, last_seq)

            consecutive_failures = 0
            sleep_s = sync_interval_s

        except _RECOVERABLE_ERRORS:
            consecutive_failures += 1
            sleep_s = _backoff_seconds(consecutive_failures)
            _log.exception(
                'sync error (consecutive_failures=%d); sleeping %.1fs before retry',
                consecutive_failures, sleep_s,
            )

        time.sleep(sleep_s)


if __name__ == '__main__':
    main()
