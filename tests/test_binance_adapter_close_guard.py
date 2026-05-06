'''Tests for PT-FIX-13: BinanceAdapter refuses session reuse after close.

Pre-fix: a `BinanceUserStream._auto_reconnect` loop that races shutdown
could call `BinanceAdapter._ensure_session()` after the adapter's
`close()` had already nulled `self._session`, silently spawning a
fresh `aiohttp.ClientSession` the adapter no longer tracked. The
session would leak through process exit.

Post-fix: `BinanceAdapter.close()` sets `self._closed = True` before
awaiting the existing session's close, and `_ensure_session()` raises
`RuntimeError` whenever `_closed` is set. A racing reconnect task
errors out cleanly instead of leaking a session.
'''

from __future__ import annotations

import pytest

from praxis.infrastructure.binance_adapter import BinanceAdapter


def _build_adapter() -> BinanceAdapter:
    return BinanceAdapter(
        base_url='https://example.test',
        ws_base_url='wss://example.test',
        ws_api_url='wss://example.test/ws-api/v3',
        credentials={},
    )


@pytest.mark.asyncio
async def test_ensure_session_raises_after_close() -> None:

    adapter = _build_adapter()
    await adapter.close()

    with pytest.raises(RuntimeError, match='closed'):
        await adapter._ensure_session()


@pytest.mark.asyncio
async def test_close_sets_closed_flag_even_with_no_session() -> None:

    adapter = _build_adapter()
    assert adapter._session is None
    assert adapter._closed is False

    await adapter.close()

    assert adapter._closed is True


@pytest.mark.asyncio
async def test_close_is_idempotent() -> None:

    adapter = _build_adapter()
    await adapter.close()
    await adapter.close()

    with pytest.raises(RuntimeError, match='closed'):
        await adapter._ensure_session()


@pytest.mark.asyncio
async def test_ensure_session_works_before_close() -> None:

    adapter = _build_adapter()
    try:
        session = await adapter._ensure_session()
        assert not session.closed
        same_session = await adapter._ensure_session()
        assert same_session is session
    finally:
        await adapter.close()
