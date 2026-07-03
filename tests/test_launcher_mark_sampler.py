'''Tests for the Launcher mark-sampler wiring.'''

from __future__ import annotations

from decimal import Decimal
from pathlib import Path
from typing import cast

import aiosqlite
import pytest

from praxis.arrow_price_store import ArrowPriceStore
from praxis.core.domain.events import MarkSampled
from praxis.infrastructure.event_spine import EventSpine
from praxis.infrastructure.venue_adapter import VenueAdapter
from praxis.launcher import InstanceConfig, Launcher
from praxis.paper.mark_sampler import MarkSampler
from praxis.trading_config import TradingConfig

from tests.test_launcher import MockVenueAdapter, _make_manifest_yaml

_ACCOUNT = 'test-acc'


async def _empty_spine() -> EventSpine:
    conn = await aiosqlite.connect(':memory:')
    spine = EventSpine(conn)
    await spine.ensure_schema()
    return spine


def _launcher(spine: EventSpine, tmp_path: Path) -> Launcher:
    exp_dir = tmp_path / 'experiment'
    exp_dir.mkdir()
    manifest_path = _make_manifest_yaml(tmp_path, exp_dir)
    config = TradingConfig(epoch_id=1, account_credentials={_ACCOUNT: ('key', 'secret')})
    inst = InstanceConfig(
        account_id=_ACCOUNT, manifest_path=manifest_path,
        strategies_base_path=tmp_path, state_dir=tmp_path / 'state',
    )

    return Launcher(
        trading_config=config, instances=[inst], event_spine=spine,
        venue_adapter=cast(VenueAdapter, MockVenueAdapter()),
    )


@pytest.mark.asyncio
async def test_build_mark_samplers_one_per_account(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(ArrowPriceStore, 'latest_close', lambda _self, _s, _i: Decimal('62000'))
    spine = await _empty_spine()
    launcher = _launcher(spine, tmp_path)

    await launcher._build_mark_samplers()
    samplers = launcher._mark_samplers

    assert len(samplers) == 1
    assert samplers[0].running

    await samplers[0].stop()
    await spine._conn.close()


@pytest.mark.asyncio
async def test_mark_sampler_appends_to_spine(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(ArrowPriceStore, 'latest_close', lambda _self, _s, _i: Decimal('62000'))
    spine = await _empty_spine()
    launcher = _launcher(spine, tmp_path)

    await launcher._build_mark_samplers()
    samplers = launcher._mark_samplers
    await samplers[0].tick_once()

    records = await spine.read(1)
    marks = [event for _seq, event in records if isinstance(event, MarkSampled)]

    assert marks
    assert marks[0].account_id == _ACCOUNT
    assert marks[0].symbol == 'BTCUSDT'
    assert marks[0].mark_price == Decimal('62000')

    await samplers[0].stop()
    await spine._conn.close()


@pytest.mark.asyncio
async def test_mark_sampler_skips_when_price_unavailable(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(ArrowPriceStore, 'latest_close', lambda _self, _s, _i: None)
    spine = await _empty_spine()
    launcher = _launcher(spine, tmp_path)

    await launcher._build_mark_samplers()
    samplers = launcher._mark_samplers
    appended = await samplers[0].tick_once()

    records = await spine.read(1)
    marks = [event for _seq, event in records if isinstance(event, MarkSampled)]

    assert appended is False
    assert marks == []

    await samplers[0].stop()
    await spine._conn.close()


@pytest.mark.asyncio
async def test_failed_build_stops_samplers_and_stays_retryable(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(ArrowPriceStore, 'latest_close', lambda _self, _s, _i: Decimal('62000'))
    spine = await _empty_spine()
    launcher = _launcher(spine, tmp_path)

    original = MarkSampler.start
    started: list[MarkSampler] = []

    def start_then_raise(self: MarkSampler) -> None:
        original(self)
        started.append(self)
        raise RuntimeError('interrupted after start')

    monkeypatch.setattr(MarkSampler, 'start', start_then_raise)

    with pytest.raises(RuntimeError, match='interrupted'):
        await launcher._build_mark_samplers()

    assert launcher._mark_samplers == []
    assert not started[0].running

    monkeypatch.setattr(MarkSampler, 'start', original)
    await launcher._build_mark_samplers()

    assert len(launcher._mark_samplers) == 1
    assert launcher._mark_samplers[0].running

    await launcher._mark_samplers[0].stop()
    await spine._conn.close()
