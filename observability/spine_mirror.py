'''Mirror Praxis event_spine.sqlite into ClickHouse on a polling cadence.'''

from __future__ import annotations

import os
import sqlite3
import sys
import time
from datetime import datetime, timezone

import clickhouse_connect


SPINE_PATH = os.environ['SPINE_PATH']
CH_HOST = os.environ['CLICKHOUSE_HOST']
CH_PORT = int(os.environ.get('CLICKHOUSE_PORT', '8123'))
CH_DATABASE = os.environ.get('CLICKHOUSE_DATABASE', 'praxis')
CH_USER = os.environ['CLICKHOUSE_USER']
CH_PASSWORD = os.environ['CLICKHOUSE_PASSWORD']
SYNC_INTERVAL_S = float(os.environ.get('SYNC_INTERVAL_SECONDS', '5'))
BATCH_SIZE = int(os.environ.get('BATCH_SIZE', '10000'))

_SCHEMA_SQL = '''
CREATE TABLE IF NOT EXISTS praxis.events (
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
    action_type LowCardinality(String) MATERIALIZED JSONExtractString(payload, 'action_type'),
    qty Decimal(38, 18) MATERIALIZED toDecimal128OrZero(JSONExtractString(payload, 'qty'), 18),
    price Decimal(38, 18) MATERIALIZED toDecimal128OrZero(JSONExtractString(payload, 'price'), 18),
    fee Decimal(38, 18) MATERIALIZED toDecimal128OrZero(JSONExtractString(payload, 'fee'), 18)
)
ENGINE = ReplacingMergeTree(event_seq)
PARTITION BY epoch_id
ORDER BY (epoch_id, event_seq)
'''


def _parse_ts(raw: str) -> datetime:

    if raw.endswith('+00:00'):
        return datetime.fromisoformat(raw)

    if raw.endswith('Z'):
        return datetime.fromisoformat(raw[:-1]).replace(tzinfo=timezone.utc)

    return datetime.fromisoformat(raw).replace(tzinfo=timezone.utc)


def _ensure_schema(ch: clickhouse_connect.driver.Client) -> None:

    ch.command(f'CREATE DATABASE IF NOT EXISTS {CH_DATABASE}')
    ch.command(_SCHEMA_SQL)


def _current_cursor(ch: clickhouse_connect.driver.Client) -> int:

    result = ch.query(f'SELECT max(event_seq) FROM {CH_DATABASE}.events').result_rows

    if not result or result[0][0] is None:
        return 0

    return int(result[0][0])


def _fetch_batch(cursor: int) -> list[tuple]:

    conn = sqlite3.connect(f'file:{SPINE_PATH}?mode=ro', uri=True)
    try:
        conn.execute('PRAGMA query_only=ON')
        rows = conn.execute(
            'SELECT event_seq, epoch_id, timestamp, event_type, payload '
            'FROM events WHERE event_seq > ? ORDER BY event_seq LIMIT ?',
            (cursor, BATCH_SIZE),
        ).fetchall()
    finally:
        conn.close()

    return rows


def _to_rows(raw_rows: list[tuple]) -> list[list]:

    out = []

    for seq, epoch, ts, event_type, payload in raw_rows:
        if isinstance(payload, bytes):
            payload = payload.decode('utf-8', errors='replace')

        out.append([
            int(seq),
            int(epoch),
            _parse_ts(ts),
            event_type,
            payload,
        ])

    return out


def main() -> None:

    print(
        f'spine-mirror: spine={SPINE_PATH} '
        f'clickhouse={CH_HOST}:{CH_PORT}/{CH_DATABASE} '
        f'interval={SYNC_INTERVAL_S:.1f}s batch={BATCH_SIZE}',
        flush=True,
    )

    ch = clickhouse_connect.get_client(
        host=CH_HOST,
        port=CH_PORT,
        database=CH_DATABASE,
        username=CH_USER,
        password=CH_PASSWORD,
    )
    _ensure_schema(ch)

    while True:
        try:
            cursor = _current_cursor(ch)
            raw_rows = _fetch_batch(cursor)

            if raw_rows:
                rows = _to_rows(raw_rows)
                ch.insert(
                    f'{CH_DATABASE}.events',
                    rows,
                    column_names=['event_seq', 'epoch_id', 'ts', 'event_type', 'payload'],
                )
                last_seq = rows[-1][0]
                print(
                    f'synced {len(rows)} rows; cursor {cursor} -> {last_seq}',
                    flush=True,
                )

        except Exception as exc:
            print(f'sync error: {type(exc).__name__}: {exc}', file=sys.stderr, flush=True)

        time.sleep(SYNC_INTERVAL_S)


if __name__ == '__main__':
    main()
