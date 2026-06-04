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

    if raw.endswith('+00:00'):
        return datetime.fromisoformat(raw)

    if raw.endswith('Z'):
        return datetime.fromisoformat(raw[:-1]).replace(tzinfo=UTC)

    return datetime.fromisoformat(raw).replace(tzinfo=UTC)


def _ensure_schema(ch: clickhouse_connect.driver.Client, database: str) -> None:

    ch.command(f'CREATE DATABASE IF NOT EXISTS {database}')
    ch.command(_SCHEMA_SQL_TEMPLATE.format(database=database))


def _current_cursor(ch: clickhouse_connect.driver.Client, database: str) -> int:

    result = ch.query(f'SELECT max(event_seq) FROM {database}.events').result_rows

    if not result or result[0][0] is None:
        return 0

    return int(result[0][0])


def _fetch_batch(spine_path: str, cursor: int, batch_size: int) -> list[tuple]:

    with sqlite3.connect(f'file:{spine_path}?mode=ro', uri=True) as conn:
        conn.execute('PRAGMA query_only=ON')
        return conn.execute(
            'SELECT event_seq, epoch_id, timestamp, event_type, payload '
            'FROM events WHERE event_seq > ? ORDER BY event_seq LIMIT ?',
            (cursor, batch_size),
        ).fetchall()


def _to_rows(raw_rows: list[tuple]) -> list[list]:

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

    return min(_BACKOFF_BASE_S * (2 ** (consecutive_failures - 1)), _BACKOFF_MAX_S)


def main() -> None:

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
