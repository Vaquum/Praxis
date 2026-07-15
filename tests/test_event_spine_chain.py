'''
Tests for the Event Spine schema migration, hash chain, and verification.
'''

from __future__ import annotations

import asyncio
import itertools
from datetime import datetime, UTC
from decimal import Decimal
from pathlib import Path

import aiosqlite
import pytest

from praxis.core.domain.enums import OrderSide
from praxis.core.domain.events import CommandAccepted, FillReceived
from praxis.infrastructure.event_spine import (
    ChainVerificationError,
    EventSpine,
    SpineSchemaError,
)

_TS = datetime(2026, 1, 1, tzinfo=UTC)
_ACCT = 'acc-1'
_EPOCH = 1
_SHA256_HEX_LEN = 64

_LEGACY_SCHEMA = '''
CREATE TABLE events (
    event_seq INTEGER PRIMARY KEY AUTOINCREMENT,
    epoch_id INTEGER NOT NULL,
    timestamp TEXT NOT NULL,
    event_type TEXT NOT NULL,
    payload BLOB NOT NULL
)'''

_GENESIS_QUERY = "SELECT value FROM spine_meta WHERE key = 'genesis_anchor'"


def _cmd(n: int) -> CommandAccepted:
    return CommandAccepted(
        account_id=_ACCT,
        timestamp=_TS,
        command_id=f'cmd-{n}',
        trade_id=f'trade-{n}',
    )


def _fill(n: int) -> FillReceived:
    return FillReceived(
        account_id=_ACCT,
        timestamp=_TS,
        client_order_id=f'ord-{n}',
        venue_order_id=f'vo-{n}',
        venue_trade_id=f'vt-{n}',
        trade_id=f'trade-{n}',
        command_id=f'cmd-{n}',
        symbol='BTCUSDT',
        side=OrderSide.BUY,
        qty=Decimal('1.5'),
        price=Decimal('50000.25'),
        fee=Decimal('0.001'),
        fee_asset='USDT',
        is_maker=True,
    )


async def _user_version(conn: aiosqlite.Connection) -> int:
    async with conn.execute('PRAGMA user_version') as cursor:
        row = await cursor.fetchone()

    assert row is not None
    return int(row[0])


async def _columns(conn: aiosqlite.Connection, table: str) -> set[str]:
    async with conn.execute(f'PRAGMA table_info({table})') as cursor:
        rows = await cursor.fetchall()

    return {row[1] for row in rows}


async def _genesis(conn: aiosqlite.Connection) -> str:
    async with conn.execute(_GENESIS_QUERY) as cursor:
        row = await cursor.fetchone()

    assert row is not None
    return row[0]


async def _make_legacy_db(path: Path, rows: int) -> None:
    async with aiosqlite.connect(str(path)) as conn:
        await conn.execute(_LEGACY_SCHEMA)
        for _ in range(rows):
            await conn.execute(
                'INSERT INTO events (epoch_id, timestamp, event_type, payload) '
                'VALUES (?, ?, ?, ?)',
                (_EPOCH, _TS.isoformat(), 'CommandAccepted', b'{}'),
            )
        await conn.commit()


@pytest.mark.asyncio
async def test_fresh_schema_sets_version_and_hash_columns() -> None:
    async with aiosqlite.connect(':memory:') as conn:
        spine = EventSpine(conn)
        await spine.ensure_schema()

        assert await _user_version(conn) == 2
        assert {'prev_hash', 'hash'} <= await _columns(conn, 'events')
        assert len(await _genesis(conn)) == _SHA256_HEX_LEN


@pytest.mark.asyncio
async def test_appends_are_hash_chained() -> None:
    async with aiosqlite.connect(':memory:') as conn:
        spine = EventSpine(conn)
        await spine.ensure_schema()
        for n in range(3):
            await spine.append(_cmd(n), _EPOCH)

        async with conn.execute(
            'SELECT event_seq, prev_hash, hash FROM events ORDER BY event_seq'
        ) as cursor:
            rows = await cursor.fetchall()

        assert all(row[1] is not None and row[2] is not None for row in rows)
        for prev, curr in itertools.pairwise(rows):
            assert curr[1] == prev[2]
        await spine.verify_chain()


@pytest.mark.asyncio
async def test_first_row_links_to_genesis_anchor() -> None:
    async with aiosqlite.connect(':memory:') as conn:
        spine = EventSpine(conn)
        await spine.ensure_schema()
        await spine.append(_cmd(0), _EPOCH)

        async with conn.execute('SELECT prev_hash FROM events WHERE event_seq = 1') as cursor:
            row = await cursor.fetchone()

        assert row is not None
        assert row[0] == await _genesis(conn)


@pytest.mark.asyncio
async def test_verify_chain_accepts_empty_spine() -> None:
    async with aiosqlite.connect(':memory:') as conn:
        spine = EventSpine(conn)
        await spine.ensure_schema()
        await spine.verify_chain()


@pytest.mark.asyncio
async def test_fill_received_is_chained_and_dedup_preserves_chain() -> None:
    async with aiosqlite.connect(':memory:') as conn:
        spine = EventSpine(conn)
        await spine.ensure_schema()

        seq = await spine.append(_fill(0), _EPOCH)
        duplicate = await spine.append(_fill(0), _EPOCH)

        assert seq == 1
        assert duplicate is None

        async with conn.execute('SELECT COUNT(*) FROM events') as cursor:
            row = await cursor.fetchone()

        assert row is not None
        assert row[0] == 1
        await spine.verify_chain()


@pytest.mark.asyncio
async def test_concurrent_appends_keep_chain_intact() -> None:
    async with aiosqlite.connect(':memory:') as conn:
        spine = EventSpine(conn)
        await spine.ensure_schema()

        seqs = await asyncio.gather(*(spine.append(_cmd(n), _EPOCH) for n in range(20)))

        assert len(set(seqs)) == 20
        await spine.verify_chain()


@pytest.mark.asyncio
async def test_legacy_db_migrates_keeps_null_prefix_and_verifies(tmp_path: Path) -> None:
    db_path = tmp_path / 'legacy.sqlite'
    await _make_legacy_db(db_path, rows=2)

    async with aiosqlite.connect(str(db_path)) as conn:
        spine = EventSpine(conn)
        await spine.ensure_schema()

        assert await _user_version(conn) == 2
        assert {'prev_hash', 'hash'} <= await _columns(conn, 'events')

        async with conn.execute('SELECT hash FROM events WHERE event_seq = 1') as cursor:
            row = await cursor.fetchone()
        assert row is not None
        assert row[0] is None

        await spine.verify_chain()

        await spine.append(_cmd(9), _EPOCH)

        async with conn.execute(
            'SELECT prev_hash, hash FROM events WHERE event_seq = 3'
        ) as cursor:
            row = await cursor.fetchone()
        assert row is not None
        assert row[0] == await _genesis(conn)
        assert row[1] is not None

        await spine.verify_chain()


@pytest.mark.asyncio
async def test_migration_is_idempotent() -> None:
    async with aiosqlite.connect(':memory:') as conn:
        spine = EventSpine(conn)
        await spine.ensure_schema()
        first_genesis = await _genesis(conn)

        await spine.ensure_schema()

        assert await _user_version(conn) == 2
        assert await _genesis(conn) == first_genesis


@pytest.mark.asyncio
async def test_newer_schema_version_is_refused() -> None:
    async with aiosqlite.connect(':memory:') as conn:
        spine = EventSpine(conn)
        await spine.ensure_schema()
        await conn.execute('PRAGMA user_version = 3')
        await conn.commit()

        with pytest.raises(SpineSchemaError):
            await spine.ensure_schema()


@pytest.mark.asyncio
async def test_failed_migration_rolls_back(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    db_path = tmp_path / 'legacy.sqlite'
    await _make_legacy_db(db_path, rows=1)

    async with aiosqlite.connect(str(db_path)) as conn:
        spine = EventSpine(conn)

        async def _boom() -> None:
            raise RuntimeError('injected migration failure')

        monkeypatch.setattr(spine, '_migrate_to_v1', _boom)

        with pytest.raises(RuntimeError):
            await spine.ensure_schema()

        assert await _user_version(conn) == 0
        assert 'hash' not in await _columns(conn, 'events')


@pytest.mark.asyncio
async def test_tampered_payload_fails_verification() -> None:
    async with aiosqlite.connect(':memory:') as conn:
        spine = EventSpine(conn)
        await spine.ensure_schema()
        for n in range(3):
            await spine.append(_cmd(n), _EPOCH)

        await conn.execute(
            'UPDATE events SET payload = ? WHERE event_seq = 2',
            (b'{"tampered": true}',),
        )
        await conn.commit()

        with pytest.raises(ChainVerificationError):
            await spine.verify_chain()


@pytest.mark.asyncio
async def test_tampered_hash_fails_verification() -> None:
    async with aiosqlite.connect(':memory:') as conn:
        spine = EventSpine(conn)
        await spine.ensure_schema()
        for n in range(3):
            await spine.append(_cmd(n), _EPOCH)

        await conn.execute(
            'UPDATE events SET hash = ? WHERE event_seq = 2',
            ('0' * _SHA256_HEX_LEN,),
        )
        await conn.commit()

        with pytest.raises(ChainVerificationError):
            await spine.verify_chain()


@pytest.mark.asyncio
async def test_deleted_row_fails_verification() -> None:
    async with aiosqlite.connect(':memory:') as conn:
        spine = EventSpine(conn)
        await spine.ensure_schema()
        for n in range(3):
            await spine.append(_cmd(n), _EPOCH)

        await conn.execute('DELETE FROM events WHERE event_seq = 2')
        await conn.commit()

        with pytest.raises(ChainVerificationError):
            await spine.verify_chain()


@pytest.mark.asyncio
async def test_unhashed_row_after_hashed_fails_verification() -> None:
    async with aiosqlite.connect(':memory:') as conn:
        spine = EventSpine(conn)
        await spine.ensure_schema()
        for n in range(2):
            await spine.append(_cmd(n), _EPOCH)

        await conn.execute(
            'INSERT INTO events (epoch_id, timestamp, event_type, payload) '
            'VALUES (?, ?, ?, ?)',
            (_EPOCH, _TS.isoformat(), 'CommandAccepted', b'{}'),
        )
        await conn.commit()

        with pytest.raises(ChainVerificationError):
            await spine.verify_chain()


async def _set_cursor(spine: EventSpine, symbol: str, trade_id: int, epoch_id: int) -> None:
    await spine.set_reconcile_cursor(
        _ACCT,
        symbol,
        last_confirmed_trade_id=trade_id,
        last_confirmed_ts=_TS.isoformat(),
        epoch_id=epoch_id,
        updated_at=_TS.isoformat(),
    )


@pytest.mark.asyncio
async def test_reconcile_cursor_missing_returns_none() -> None:
    async with aiosqlite.connect(':memory:') as conn:
        spine = EventSpine(conn)
        await spine.ensure_schema()

        assert await spine.get_reconcile_cursor(_ACCT, 'BTCUSDT') is None


@pytest.mark.asyncio
async def test_reconcile_cursor_set_and_get() -> None:
    async with aiosqlite.connect(':memory:') as conn:
        spine = EventSpine(conn)
        await spine.ensure_schema()
        await _set_cursor(spine, 'BTCUSDT', 105, _EPOCH)

        assert await spine.get_reconcile_cursor(_ACCT, 'BTCUSDT') == 105


@pytest.mark.asyncio
async def test_reconcile_cursor_upsert_overwrites() -> None:
    async with aiosqlite.connect(':memory:') as conn:
        spine = EventSpine(conn)
        await spine.ensure_schema()
        await _set_cursor(spine, 'BTCUSDT', 105, _EPOCH)
        await _set_cursor(spine, 'BTCUSDT', 220, _EPOCH)

        assert await spine.get_reconcile_cursor(_ACCT, 'BTCUSDT') == 220


@pytest.mark.asyncio
async def test_reconcile_cursor_is_per_symbol_and_cross_epoch() -> None:
    async with aiosqlite.connect(':memory:') as conn:
        spine = EventSpine(conn)
        await spine.ensure_schema()
        await _set_cursor(spine, 'BTCUSDT', 10, 1)
        await _set_cursor(spine, 'ETHUSDT', 99, 2)

        assert await spine.get_reconcile_cursor(_ACCT, 'BTCUSDT') == 10
        assert await spine.get_reconcile_cursor(_ACCT, 'ETHUSDT') == 99


@pytest.mark.asyncio
async def test_v1_db_gains_cursor_table_on_migration() -> None:
    async with aiosqlite.connect(':memory:') as conn:
        spine = EventSpine(conn)
        await spine.ensure_schema()
        await conn.execute('DROP TABLE reconcile_cursor')
        await conn.execute('PRAGMA user_version = 1')
        await conn.commit()

        await EventSpine(conn).ensure_schema()

        assert await _user_version(conn) == 2
        await _set_cursor(spine, 'BTCUSDT', 1, _EPOCH)
        assert await spine.get_reconcile_cursor(_ACCT, 'BTCUSDT') == 1
