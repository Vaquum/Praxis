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
import orjson
import pytest

from praxis.core.domain.enums import OrderSide
from praxis.core.domain.events import CommandAccepted, FillReceived
from praxis.infrastructure import event_spine
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


async def _table_exists(conn: aiosqlite.Connection, name: str) -> bool:
    async with conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?", (name,),
    ) as cursor:
        return await cursor.fetchone() is not None


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

        assert await _user_version(conn) == 4
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

        assert await _user_version(conn) == 4
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

        assert await _user_version(conn) == 4
        assert await _genesis(conn) == first_genesis


@pytest.mark.asyncio
async def test_newer_schema_version_is_refused() -> None:
    async with aiosqlite.connect(':memory:') as conn:
        spine = EventSpine(conn)
        await spine.ensure_schema()
        await conn.execute('PRAGMA user_version = 5')
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
async def test_set_reconcile_cursor_serializes_under_append_lock() -> None:
    async with aiosqlite.connect(':memory:') as conn:
        spine = EventSpine(conn)
        await spine.ensure_schema()

        await spine._append_lock.acquire()
        task = asyncio.ensure_future(_set_cursor(spine, 'BTCUSDT', 105, _EPOCH))
        await asyncio.sleep(0)

        assert not task.done()

        spine._append_lock.release()
        await task

        assert await spine.get_reconcile_cursor(_ACCT, 'BTCUSDT') == 105


@pytest.mark.asyncio
async def test_set_reconcile_cursor_rolls_back_on_commit_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async with aiosqlite.connect(':memory:') as conn:
        spine = EventSpine(conn)
        await spine.ensure_schema()

        rolled_back = False
        real_rollback = conn.rollback

        async def _boom() -> None:
            raise RuntimeError('commit failed')

        async def _track_rollback() -> None:
            nonlocal rolled_back
            rolled_back = True
            await real_rollback()

        monkeypatch.setattr(conn, 'commit', _boom)
        monkeypatch.setattr(conn, 'rollback', _track_rollback)

        with pytest.raises(RuntimeError, match='commit failed'):
            await _set_cursor(spine, 'BTCUSDT', 105, _EPOCH)

        assert rolled_back


@pytest.mark.asyncio
async def test_append_rolls_back_on_commit_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    async with aiosqlite.connect(':memory:') as conn:
        spine = EventSpine(conn)
        await spine.ensure_schema()

        rolled_back = False
        real_rollback = conn.rollback

        async def _boom() -> None:
            raise RuntimeError('commit failed')

        async def _track_rollback() -> None:
            nonlocal rolled_back
            rolled_back = True
            await real_rollback()

        monkeypatch.setattr(conn, 'commit', _boom)
        monkeypatch.setattr(conn, 'rollback', _track_rollback)

        with pytest.raises(RuntimeError, match='commit failed'):
            await spine.append(_cmd(0), _EPOCH)

        assert rolled_back


@pytest.mark.asyncio
async def test_v1_db_gains_cursor_table_on_migration() -> None:
    async with aiosqlite.connect(':memory:') as conn:
        spine = EventSpine(conn)
        await spine.ensure_schema()
        await conn.execute('DROP TABLE reconcile_cursor')
        await conn.execute('PRAGMA user_version = 1')
        await conn.commit()

        await EventSpine(conn).ensure_schema()

        assert await _user_version(conn) == 4
        await _set_cursor(spine, 'BTCUSDT', 1, _EPOCH)
        assert await spine.get_reconcile_cursor(_ACCT, 'BTCUSDT') == 1


def _fill_symbol(symbol: str, trade_id: str, *, client: str = 'ord') -> FillReceived:
    return FillReceived(
        account_id=_ACCT,
        timestamp=_TS,
        client_order_id=client,
        venue_order_id='vo',
        venue_trade_id=trade_id,
        trade_id='trade',
        command_id='cmd',
        symbol=symbol,
        side=OrderSide.BUY,
        qty=Decimal('1'),
        price=Decimal('50000'),
        fee=Decimal('0.001'),
        fee_asset='USDT',
        is_maker=True,
    )


@pytest.mark.asyncio
async def test_same_trade_id_different_symbol_both_apply() -> None:
    async with aiosqlite.connect(':memory:') as conn:
        spine = EventSpine(conn)
        await spine.ensure_schema()

        s1 = await spine.append(_fill_symbol('BTCUSDT', 'vt-100'), _EPOCH)
        s2 = await spine.append(_fill_symbol('ETHUSDT', 'vt-100', client='ord2'), _EPOCH)

        assert s1 is not None
        assert s2 is not None
        assert s1 != s2


@pytest.mark.asyncio
async def test_duplicate_fill_same_symbol_dropped() -> None:
    async with aiosqlite.connect(':memory:') as conn:
        spine = EventSpine(conn)
        await spine.ensure_schema()

        assert await spine.append(_fill_symbol('BTCUSDT', 'vt-1'), _EPOCH) is not None
        assert await spine.append(_fill_symbol('BTCUSDT', 'vt-1'), _EPOCH) is None


@pytest.mark.asyncio
async def test_multi_symbol_history_fails_closed_on_migration() -> None:
    async with aiosqlite.connect(':memory:') as conn:
        spine = EventSpine(conn)
        await spine.ensure_schema()
        await spine.append(_fill_symbol('BTCUSDT', 'vt-1'), _EPOCH)
        await spine.append(_fill_symbol('ETHUSDT', 'vt-2'), _EPOCH)
        await conn.execute('PRAGMA user_version = 2')
        await conn.commit()

        with pytest.raises(SpineSchemaError, match='spans'):
            await EventSpine(conn).ensure_schema()


@pytest.mark.asyncio
async def test_unmatched_legacy_dedup_row_fails_closed() -> None:
    async with aiosqlite.connect(':memory:') as conn:
        spine = EventSpine(conn)
        await spine.ensure_schema()
        await conn.execute(
            'CREATE TABLE IF NOT EXISTS fill_dedup (epoch_id INTEGER, '
            'account_id TEXT, dedup_key TEXT, UNIQUE(epoch_id, account_id, dedup_key))'
        )
        await conn.execute(
            'INSERT INTO fill_dedup (epoch_id, account_id, dedup_key) VALUES (?, ?, ?)',
            (_EPOCH, _ACCT, 'orphan-id'),
        )
        await conn.execute('PRAGMA user_version = 2')
        await conn.commit()

        with pytest.raises(SpineSchemaError, match='no matching'):
            await EventSpine(conn).ensure_schema()


@pytest.mark.asyncio
async def test_cross_account_same_trade_id_orphan_fails_closed() -> None:
    async with aiosqlite.connect(':memory:') as conn:
        await conn.execute(_LEGACY_SCHEMA)
        await conn.execute(
            'CREATE TABLE fill_dedup (epoch_id INTEGER, account_id TEXT, dedup_key TEXT, '
            'UNIQUE(epoch_id, account_id, dedup_key))'
        )
        payload = orjson.dumps(
            {'symbol': 'BTCUSDT', 'account_id': 'acc-A', 'venue_trade_id': 'vt-900'},
        )
        await conn.execute(
            'INSERT INTO events (epoch_id, timestamp, event_type, payload) VALUES (?, ?, ?, ?)',
            (_EPOCH, _TS.isoformat(), 'FillReceived', payload),
        )
        await conn.execute(
            'INSERT INTO fill_dedup (epoch_id, account_id, dedup_key) VALUES (?, ?, ?)',
            (_EPOCH, 'acc-A', 'vt-900'),
        )
        await conn.execute(
            'INSERT INTO fill_dedup (epoch_id, account_id, dedup_key) VALUES (?, ?, ?)',
            (_EPOCH, 'acc-B', 'vt-900'),
        )
        await conn.execute('PRAGMA user_version = 2')
        await conn.commit()

        with pytest.raises(SpineSchemaError, match='no matching'):
            await EventSpine(conn).ensure_schema()


@pytest.mark.asyncio
async def test_malformed_fill_payload_fails_closed_on_migration() -> None:
    async with aiosqlite.connect(':memory:') as conn:
        spine = EventSpine(conn)
        await spine.ensure_schema()
        await spine.append(_fill_symbol('BTCUSDT', 'vt-1'), _EPOCH)
        await conn.execute(
            "UPDATE events SET payload = ? WHERE event_type = 'FillReceived'",
            (orjson.dumps({'venue_trade_id': 'vt-1'}),),
        )
        await conn.execute('PRAGMA user_version = 2')
        await conn.commit()

        with pytest.raises(SpineSchemaError, match='malformed'):
            await EventSpine(conn).ensure_schema()


@pytest.mark.asyncio
async def test_non_string_fill_field_fails_closed_on_migration() -> None:
    async with aiosqlite.connect(':memory:') as conn:
        spine = EventSpine(conn)
        await spine.ensure_schema()
        await spine.append(_fill_symbol('BTCUSDT', 'vt-1'), _EPOCH)
        await conn.execute(
            "UPDATE events SET payload = ? WHERE event_type = 'FillReceived'",
            (orjson.dumps({'symbol': 123, 'account_id': _ACCT, 'venue_trade_id': 'vt-1'}),),
        )
        await conn.execute('PRAGMA user_version = 2')
        await conn.commit()

        with pytest.raises(SpineSchemaError, match='malformed'):
            await EventSpine(conn).ensure_schema()


@pytest.mark.asyncio
async def test_legacy_dedup_rows_fold_into_v2_and_table_is_dropped() -> None:
    async with aiosqlite.connect(':memory:') as conn:
        await conn.execute(_LEGACY_SCHEMA)
        await conn.execute(
            'CREATE TABLE fill_dedup (epoch_id INTEGER, account_id TEXT, dedup_key TEXT, '
            'UNIQUE(epoch_id, account_id, dedup_key))'
        )
        payload = orjson.dumps(
            {'symbol': 'BTCUSDT', 'account_id': _ACCT, 'venue_trade_id': 'vt-500'},
        )
        await conn.execute(
            'INSERT INTO events (epoch_id, timestamp, event_type, payload) VALUES (?, ?, ?, ?)',
            (_EPOCH, _TS.isoformat(), 'FillReceived', payload),
        )
        await conn.execute(
            'INSERT INTO fill_dedup (epoch_id, account_id, dedup_key) VALUES (?, ?, ?)',
            (_EPOCH, _ACCT, 'vt-500'),
        )
        await conn.execute('PRAGMA user_version = 2')
        await conn.commit()

        spine = EventSpine(conn)
        await spine.ensure_schema()

        async with conn.execute(
            'SELECT symbol FROM fill_dedup_v2 WHERE dedup_key = ?', ('vt-500',),
        ) as cursor:
            folded = [str(row[0]) for row in await cursor.fetchall()]

        assert folded == ['BTCUSDT']
        assert not await _table_exists(conn, 'fill_dedup')

        assert await spine.append(_fill_symbol('ETHUSDT', 'vt-500'), _EPOCH) is not None
        assert await spine.append(_fill_symbol('BTCUSDT', 'vt-500'), _EPOCH) is None


@pytest.mark.asyncio
async def test_v3_db_folds_legacy_rows_and_keeps_dedup() -> None:
    '''A database already stamped v3 was proven but never had its legacy rows
    copied into v2 — it depended on the dual-read. v4 folds them, so the same
    fill is still suppressed once the dual-read is gone.'''

    async with aiosqlite.connect(':memory:') as conn:
        spine = EventSpine(conn)
        await spine.ensure_schema()
        await conn.execute(
            'CREATE TABLE IF NOT EXISTS fill_dedup (epoch_id INTEGER, '
            'account_id TEXT, dedup_key TEXT, UNIQUE(epoch_id, account_id, dedup_key))'
        )
        await conn.execute(
            'INSERT INTO fill_dedup (epoch_id, account_id, dedup_key) VALUES (?, ?, ?)',
            (_EPOCH, _ACCT, 'vt-v3'),
        )
        await conn.execute(
            'INSERT OR REPLACE INTO spine_meta (key, value) VALUES (?, ?)',
            ('legacy_dedup_symbol', 'BTCUSDT'),
        )
        await conn.execute('PRAGMA user_version = 3')
        await conn.commit()

        migrated = EventSpine(conn)
        await migrated.ensure_schema()

        assert await _user_version(conn) == 4
        assert not await _table_exists(conn, 'fill_dedup')
        assert await migrated.append(_fill_symbol('BTCUSDT', 'vt-v3'), _EPOCH) is None
        assert await migrated.append(_fill_symbol('ETHUSDT', 'vt-v3'), _EPOCH) is not None


@pytest.mark.asyncio
async def test_v3_db_with_multi_symbol_history_still_opens() -> None:
    '''The v3 proof must not re-run on a database already stamped v3: it has
    since accumulated legitimate multi-symbol history that the proof would
    reject, and re-proving an already-proven database is not v4's business.'''

    async with aiosqlite.connect(':memory:') as conn:
        spine = EventSpine(conn)
        await spine.ensure_schema()
        await spine.append(_fill_symbol('BTCUSDT', 'vt-multi-1'), _EPOCH)
        await spine.append(_fill_symbol('ETHUSDT', 'vt-multi-2'), _EPOCH)
        await conn.execute('PRAGMA user_version = 3')
        await conn.commit()

        await EventSpine(conn).ensure_schema()

        assert await _user_version(conn) == 4


@pytest.mark.asyncio
async def test_legacy_rows_without_proven_symbol_fail_closed() -> None:
    '''A legacy row whose symbol was never proven cannot be folded: writing it
    under an empty symbol would create a dedup key that matches nothing.'''

    async with aiosqlite.connect(':memory:') as conn:
        spine = EventSpine(conn)
        await spine.ensure_schema()
        await conn.execute(
            'CREATE TABLE IF NOT EXISTS fill_dedup (epoch_id INTEGER, '
            'account_id TEXT, dedup_key TEXT, UNIQUE(epoch_id, account_id, dedup_key))'
        )
        await conn.execute(
            'INSERT INTO fill_dedup (epoch_id, account_id, dedup_key) VALUES (?, ?, ?)',
            (_EPOCH, _ACCT, 'vt-unproven'),
        )
        await conn.execute('PRAGMA user_version = 3')
        await conn.commit()

        with pytest.raises(SpineSchemaError, match='no proven symbol'):
            await EventSpine(conn).ensure_schema()


@pytest.mark.asyncio
async def test_v4_reopen_does_not_recreate_legacy_table() -> None:
    '''The legacy table is created only by the v3 proof, so a migrated database
    does not grow it back on every open.'''

    async with aiosqlite.connect(':memory:') as conn:
        await EventSpine(conn).ensure_schema()
        await EventSpine(conn).ensure_schema()

        assert await _user_version(conn) == 4
        assert not await _table_exists(conn, 'fill_dedup')


@pytest.mark.asyncio
async def test_v4_resumes_after_interruption_between_drop_and_stamp() -> None:
    '''A crash after the drop but before the version stamp leaves a v3-stamped
    database with no legacy table; reopening must complete rather than fail on
    the missing table.'''

    async with aiosqlite.connect(':memory:') as conn:
        await EventSpine(conn).ensure_schema()
        await conn.execute('PRAGMA user_version = 3')
        await conn.commit()

        await EventSpine(conn).ensure_schema()

        assert await _user_version(conn) == 4


@pytest.mark.asyncio
async def test_v4_folds_legacy_rows_that_already_exist_in_v2() -> None:
    '''A legacy row the v2 table already holds is not a conflict: the backfill
    ignores it and the coverage check still finds it, so the drop proceeds.'''

    async with aiosqlite.connect(':memory:') as conn:
        spine = EventSpine(conn)
        await spine.ensure_schema()
        await spine.append(_fill_symbol('BTCUSDT', 'vt-overlap'), _EPOCH)
        await conn.execute(
            'CREATE TABLE IF NOT EXISTS fill_dedup (epoch_id INTEGER, '
            'account_id TEXT, dedup_key TEXT, UNIQUE(epoch_id, account_id, dedup_key))'
        )
        await conn.executemany(
            'INSERT INTO fill_dedup (epoch_id, account_id, dedup_key) VALUES (?, ?, ?)',
            [(_EPOCH, _ACCT, 'vt-overlap'), (_EPOCH, _ACCT, 'vt-legacy-only')],
        )
        await conn.execute(
            'INSERT OR REPLACE INTO spine_meta (key, value) VALUES (?, ?)',
            ('legacy_dedup_symbol', 'BTCUSDT'),
        )
        await conn.execute('PRAGMA user_version = 3')
        await conn.commit()

        migrated = EventSpine(conn)
        await migrated.ensure_schema()

        assert not await _table_exists(conn, 'fill_dedup')
        assert await migrated.append(_fill_symbol('BTCUSDT', 'vt-legacy-only'), _EPOCH) is None


@pytest.mark.asyncio
async def test_v4_refuses_to_drop_when_a_legacy_row_is_uncovered(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    '''Coverage is proven per key, not by counting: a v2 table holding the same
    number of rows under the proven symbol does not make the legacy rows safe
    to discard.'''

    async with aiosqlite.connect(':memory:') as conn:
        spine = EventSpine(conn)
        await spine.ensure_schema()
        await conn.execute(
            'CREATE TABLE IF NOT EXISTS fill_dedup (epoch_id INTEGER, '
            'account_id TEXT, dedup_key TEXT, UNIQUE(epoch_id, account_id, dedup_key))'
        )
        await conn.execute(
            'INSERT INTO fill_dedup (epoch_id, account_id, dedup_key) VALUES (?, ?, ?)',
            (_EPOCH, _ACCT, 'vt-uncovered'),
        )
        await conn.execute(
            'INSERT OR REPLACE INTO spine_meta (key, value) VALUES (?, ?)',
            ('legacy_dedup_symbol', 'BTCUSDT'),
        )
        await conn.execute('PRAGMA user_version = 3')
        await conn.commit()

        monkeypatch.setattr(
            event_spine,
            '_DEDUP_V2_BACKFILL',
            'INSERT OR IGNORE INTO fill_dedup_v2 '
            '(epoch_id, account_id, symbol, dedup_key) '
            "SELECT epoch_id, account_id, ?, 'other-key' FROM fill_dedup",
        )

        with pytest.raises(SpineSchemaError, match='absent from fill_dedup_v2'):
            await EventSpine(conn).ensure_schema()

        assert await _table_exists(conn, 'fill_dedup')


@pytest.mark.asyncio
async def test_v4_resumes_when_rows_were_already_folded() -> None:
    '''A crash after the backfill but before the drop leaves both tables
    populated; reopening folds the same rows again harmlessly and completes.'''

    async with aiosqlite.connect(':memory:') as conn:
        spine = EventSpine(conn)
        await spine.ensure_schema()
        await conn.execute(
            'CREATE TABLE IF NOT EXISTS fill_dedup (epoch_id INTEGER, '
            'account_id TEXT, dedup_key TEXT, UNIQUE(epoch_id, account_id, dedup_key))'
        )
        await conn.execute(
            'INSERT INTO fill_dedup (epoch_id, account_id, dedup_key) VALUES (?, ?, ?)',
            (_EPOCH, _ACCT, 'vt-resume'),
        )
        await conn.execute(
            'INSERT OR IGNORE INTO fill_dedup_v2 '
            '(epoch_id, account_id, symbol, dedup_key) VALUES (?, ?, ?, ?)',
            (_EPOCH, _ACCT, 'BTCUSDT', 'vt-resume'),
        )
        await conn.execute(
            'INSERT OR REPLACE INTO spine_meta (key, value) VALUES (?, ?)',
            ('legacy_dedup_symbol', 'BTCUSDT'),
        )
        await conn.execute('PRAGMA user_version = 3')
        await conn.commit()

        migrated = EventSpine(conn)
        await migrated.ensure_schema()

        assert await _user_version(conn) == 4
        assert not await _table_exists(conn, 'fill_dedup')
        assert await migrated.append(_fill_symbol('BTCUSDT', 'vt-resume'), _EPOCH) is None


@pytest.mark.asyncio
async def test_v4_resumes_after_drop_with_rows_already_folded() -> None:
    '''The crash window that matters: the rows were folded and the table
    dropped, but the version never advanced. Reopening must complete the stamp
    and leave the folded dedup intact rather than fail on the missing table.'''

    async with aiosqlite.connect(':memory:') as conn:
        spine = EventSpine(conn)
        await spine.ensure_schema()
        await conn.execute(
            'INSERT OR IGNORE INTO fill_dedup_v2 '
            '(epoch_id, account_id, symbol, dedup_key) VALUES (?, ?, ?, ?)',
            (_EPOCH, _ACCT, 'BTCUSDT', 'vt-folded'),
        )
        await conn.execute('PRAGMA user_version = 3')
        await conn.commit()

        assert not await _table_exists(conn, 'fill_dedup')

        migrated = EventSpine(conn)
        await migrated.ensure_schema()

        assert await _user_version(conn) == 4
        assert await migrated.append(_fill_symbol('BTCUSDT', 'vt-folded'), _EPOCH) is None


@pytest.mark.asyncio
async def test_legacy_rows_with_stored_empty_symbol_fail_closed() -> None:
    '''An empty proven symbol is not a symbol. Folding rows under it would key
    them to something no fill can carry, and the coverage check would then
    bless the loss, so the migration refuses.'''

    async with aiosqlite.connect(':memory:') as conn:
        spine = EventSpine(conn)
        await spine.ensure_schema()
        await conn.execute(
            'CREATE TABLE IF NOT EXISTS fill_dedup (epoch_id INTEGER, '
            'account_id TEXT, dedup_key TEXT, UNIQUE(epoch_id, account_id, dedup_key))'
        )
        await conn.execute(
            'INSERT INTO fill_dedup (epoch_id, account_id, dedup_key) VALUES (?, ?, ?)',
            (_EPOCH, _ACCT, 'vt-empty-symbol'),
        )
        await conn.execute(
            'INSERT OR REPLACE INTO spine_meta (key, value) VALUES (?, ?)',
            ('legacy_dedup_symbol', ''),
        )
        await conn.execute('PRAGMA user_version = 3')
        await conn.commit()

        with pytest.raises(SpineSchemaError, match='no proven symbol'):
            await EventSpine(conn).ensure_schema()

        assert await _table_exists(conn, 'fill_dedup')


async def _set_meta(conn: aiosqlite.Connection, key: str, value: str) -> None:
    await conn.execute(
        'INSERT OR REPLACE INTO spine_meta (key, value) VALUES (?, ?)', (key, value),
    )
    await conn.commit()


@pytest.mark.asyncio
@pytest.mark.parametrize('key', ['chain_version', 'genesis_anchor'])
async def test_missing_chain_identity_is_refused(key: str) -> None:
    '''A database that records nothing about the chain it holds cannot be
    attributed to this build, so it is refused rather than adopted.'''

    async with aiosqlite.connect(':memory:') as conn:
        await EventSpine(conn).ensure_schema()
        await conn.execute('DELETE FROM spine_meta WHERE key = ?', (key,))
        await conn.commit()

        with pytest.raises(SpineSchemaError, match=f'missing {key!r}'):
            await EventSpine(conn).ensure_schema()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ('key', 'stale'),
    [
        ('chain_version', '2'),
        ('genesis_anchor', 'a' * 64),
    ],
)
async def test_foreign_chain_identity_is_refused(key: str, stale: str) -> None:
    '''A stale value is the case presence alone would accept.

    The metadata is written with INSERT OR IGNORE, so a database already
    holding another build's value keeps it silently. Its events are already
    hashed under that dialect, which no migration can reconcile.
    '''

    async with aiosqlite.connect(':memory:') as conn:
        await EventSpine(conn).ensure_schema()
        await _set_meta(conn, key, stale)

        with pytest.raises(SpineSchemaError, match='another dialect'):
            await EventSpine(conn).ensure_schema()


@pytest.mark.asyncio
async def test_chain_identity_checked_before_v4_migrates() -> None:
    '''A database arriving mid-version is checked before anything mutates it.

    The legacy dedup table is what v4 would drop, so it standing afterwards
    is the evidence that nothing ran: were the check to move after v4, the
    table would be gone and its rows folded before the chain was ever found
    to be foreign.
    '''

    async with aiosqlite.connect(':memory:') as conn:
        await EventSpine(conn).ensure_schema()
        await conn.execute(
            'CREATE TABLE IF NOT EXISTS fill_dedup (epoch_id INTEGER, '
            'account_id TEXT, dedup_key TEXT, UNIQUE(epoch_id, account_id, dedup_key))'
        )
        await conn.execute(
            'INSERT INTO fill_dedup (epoch_id, account_id, dedup_key) VALUES (?, ?, ?)',
            (_EPOCH, _ACCT, 'vt-foreign'),
        )
        await _set_meta(conn, 'genesis_anchor', 'b' * 64)
        await conn.execute('PRAGMA user_version = 3')
        await conn.commit()

        with pytest.raises(SpineSchemaError, match='another dialect'):
            await EventSpine(conn).ensure_schema()

        assert await _user_version(conn) == 3
        assert await _table_exists(conn, 'fill_dedup')
