'''
Tests for praxis.infrastructure.binance_ws.
'''

from __future__ import annotations

import asyncio
import json
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import aiohttp

from praxis.infrastructure.binance_ws import BinanceUserStream
from praxis.infrastructure.venue_adapter import VenueError


_ACCOUNT_ID = 'test-account'


def _make_adapter(base_url: str = 'https://testnet.binance.vision') -> Any:

    '''
    Create a mock BinanceAdapter with stubbed listen key methods.

    Args:
        base_url (str): Base URL for the adapter

    Returns:
        Any: Mock adapter with async listen key method stubs
    '''

    adapter = MagicMock()
    adapter._base_url = base_url
    adapter._create_listen_key = AsyncMock(return_value='listen-key')
    adapter._keepalive_listen_key = AsyncMock()
    adapter._close_listen_key = AsyncMock()
    adapter._ensure_session = AsyncMock()
    return adapter


class _AsyncIter:

    '''
    Async iterator wrapper for simulating WebSocket message streams.
    '''

    def __init__(self, items: list[Any]) -> None:
        self._items = iter(items)

    def __aiter__(self) -> _AsyncIter:
        return self

    async def __anext__(self) -> Any:
        try:
            return next(self._items)
        except StopIteration:
            raise StopAsyncIteration from None


class TestBinanceUserStream:

    def test_build_ws_url_https(self) -> None:
        adapter = _make_adapter('https://testnet.binance.vision')
        stream = BinanceUserStream(adapter=adapter, account_id=_ACCOUNT_ID)
        result = stream._build_ws_url('abc123')
        assert result == 'wss://testnet.binance.vision/ws/abc123'

    def test_build_ws_url_invalid_scheme_raises(self) -> None:
        adapter = _make_adapter('ftp://example.com')
        stream = BinanceUserStream(adapter=adapter, account_id=_ACCOUNT_ID)
        with pytest.raises(ValueError, match='Unsupported base URL scheme'):
            stream._build_ws_url('abc123')

    @pytest.mark.asyncio
    async def test_connect_creates_listen_key_and_starts_keepalive(self) -> None:
        adapter = _make_adapter()
        ws = AsyncMock()
        ws.closed = False
        session = MagicMock()
        session.ws_connect = AsyncMock(return_value=ws)
        adapter._ensure_session.return_value = session

        stream = BinanceUserStream(
            adapter=adapter,
            account_id=_ACCOUNT_ID,
            keepalive_interval_seconds=9999,
        )
        await stream.initiate_connection()

        adapter._create_listen_key.assert_awaited_once_with(_ACCOUNT_ID)
        session.ws_connect.assert_awaited_once_with(
            'wss://testnet.binance.vision/ws/listen-key',
        )
        assert stream.listen_key == 'listen-key'
        assert stream.websocket is ws
        assert stream._keepalive_task is not None

        await stream.close()

    @pytest.mark.asyncio
    async def test_connect_skips_when_already_connected(self) -> None:

        adapter = _make_adapter()
        ws = AsyncMock()
        ws.closed = False
        session = MagicMock()
        session.ws_connect = AsyncMock(return_value=ws)
        adapter._ensure_session.return_value = session

        stream = BinanceUserStream(
            adapter=adapter,
            account_id=_ACCOUNT_ID,
            keepalive_interval_seconds=9999,
        )
        await stream.initiate_connection()
        adapter._create_listen_key.reset_mock()

        await stream.initiate_connection()

        adapter._create_listen_key.assert_not_awaited()

        await stream.close()

    @pytest.mark.asyncio
    async def test_connect_skips_when_reconnect_task_running(self) -> None:
        adapter = _make_adapter()
        ws = AsyncMock()
        ws.closed = False
        ws.__aiter__ = MagicMock(return_value=_AsyncIter([]))
        session = MagicMock()
        session.ws_connect = AsyncMock(return_value=ws)
        adapter._ensure_session.return_value = session

        callback = AsyncMock()
        stream = BinanceUserStream(
            adapter=adapter,
            account_id=_ACCOUNT_ID,
            on_message=callback,
            keepalive_interval_seconds=9999,
        )
        await stream.initiate_connection()
        assert stream._reconnect_task is not None

        stream._ws = None
        adapter._create_listen_key.reset_mock()

        await stream.initiate_connection()

        adapter._create_listen_key.assert_not_awaited()

        await stream.close()
    @pytest.mark.asyncio
    async def test_connect_cleans_stale_listen_key_on_closed_ws(self) -> None:

        adapter = _make_adapter()
        ws = AsyncMock()
        ws.closed = False
        session = MagicMock()
        session.ws_connect = AsyncMock(return_value=ws)
        adapter._ensure_session.return_value = session

        stream = BinanceUserStream(
            adapter=adapter,
            account_id=_ACCOUNT_ID,
            keepalive_interval_seconds=9999,
        )
        await stream.initiate_connection()
        assert stream._listen_key == 'listen-key'

        ws.closed = True
        adapter._close_listen_key.reset_mock()
        new_ws = AsyncMock()
        new_ws.closed = False
        session.ws_connect.return_value = new_ws
        adapter._create_listen_key.return_value = 'new-listen-key'

        await stream.initiate_connection()

        adapter._close_listen_key.assert_any_await(_ACCOUNT_ID, 'listen-key')
        assert stream._listen_key == 'new-listen-key'

        await stream.close()

    @pytest.mark.asyncio
    async def test_connect_failure_closes_listen_key(self) -> None:
        adapter = _make_adapter()
        session = MagicMock()
        session.ws_connect = AsyncMock(side_effect=aiohttp.ClientError('boom'))
        adapter._ensure_session.return_value = session

        stream = BinanceUserStream(adapter=adapter, account_id=_ACCOUNT_ID)
        with pytest.raises(aiohttp.ClientError, match='boom'):
            await stream.initiate_connection()

        adapter._close_listen_key.assert_awaited_once_with(_ACCOUNT_ID, 'listen-key')

    @pytest.mark.asyncio
    async def test_close_shuts_down_resources(self) -> None:
        adapter = _make_adapter()
        ws = AsyncMock()
        ws.closed = False
        session = MagicMock()
        session.ws_connect = AsyncMock(return_value=ws)
        adapter._ensure_session.return_value = session

        stream = BinanceUserStream(
            adapter=adapter,
            account_id=_ACCOUNT_ID,
            keepalive_interval_seconds=9999,
        )
        await stream.initiate_connection()
        await stream.close()

        ws.close.assert_awaited_once()
        adapter._close_listen_key.assert_awaited_once_with(_ACCOUNT_ID, 'listen-key')
        assert stream.listen_key is None
        assert stream.websocket is None
        assert stream._keepalive_task is None

    @pytest.mark.asyncio
    async def test_keepalive_loop_exits_when_listen_key_missing(self) -> None:
        adapter = _make_adapter()
        stream = BinanceUserStream(
            adapter=adapter,
            account_id=_ACCOUNT_ID,
            keepalive_interval_seconds=0,
        )
        await stream._keepalive_loop()
        adapter._keepalive_listen_key.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_async_context_manager_connects_and_closes(self) -> None:
        adapter = _make_adapter()
        ws = AsyncMock()
        ws.closed = False
        session = MagicMock()
        session.ws_connect = AsyncMock(return_value=ws)
        adapter._ensure_session.return_value = session

        async with BinanceUserStream(
            adapter=adapter,
            account_id=_ACCOUNT_ID,
            keepalive_interval_seconds=9999,
        ) as stream:
            assert stream.listen_key == 'listen-key'

        adapter._close_listen_key.assert_awaited_once_with(_ACCOUNT_ID, 'listen-key')

    @pytest.mark.asyncio
    async def test_initiate_connection_with_on_message_starts_reconnect_task(self) -> None:
        adapter = _make_adapter()
        ws = AsyncMock()
        ws.closed = False
        ws.__aiter__ = MagicMock(return_value=_AsyncIter([]))
        session = MagicMock()
        session.ws_connect = AsyncMock(return_value=ws)
        adapter._ensure_session.return_value = session

        callback = AsyncMock()
        stream = BinanceUserStream(
            adapter=adapter,
            account_id=_ACCOUNT_ID,
            on_message=callback,
            keepalive_interval_seconds=9999,
        )
        await stream.initiate_connection()

        assert stream._reconnect_task is not None
        await stream.close()

    @pytest.mark.asyncio
    async def test_receive_loop_dispatches_json_text_frame(self) -> None:
        adapter = _make_adapter()
        payload = {'e': 'executionReport', 's': 'BTCUSDT'}
        msg = MagicMock()
        msg.type = aiohttp.WSMsgType.TEXT
        msg.data = json.dumps(payload)

        ws = _AsyncIter([msg])

        callback = AsyncMock()
        stream = BinanceUserStream(
            adapter=adapter,
            account_id=_ACCOUNT_ID,
            on_message=callback,
        )
        stream._ws = ws  # type: ignore[assignment]

        await stream._receive_loop()
        callback.assert_awaited_once_with(payload)

    @pytest.mark.asyncio
    async def test_receive_loop_skips_non_json_frame(self) -> None:
        adapter = _make_adapter()
        msg = MagicMock()
        msg.type = aiohttp.WSMsgType.TEXT
        msg.data = 'not-json'

        ws = _AsyncIter([msg])

        callback = AsyncMock()
        stream = BinanceUserStream(
            adapter=adapter,
            account_id=_ACCOUNT_ID,
            on_message=callback,
        )
        stream._ws = ws  # type: ignore[assignment]

        with patch('praxis.infrastructure.binance_ws._log') as mock_logger:
            await stream._receive_loop()
            mock_logger.warning.assert_called_once()

        callback.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_receive_loop_survives_callback_exception(self) -> None:
        adapter = _make_adapter()
        payload_1 = {'e': 'first'}
        payload_2 = {'e': 'second'}
        msg_1 = MagicMock()
        msg_1.type = aiohttp.WSMsgType.TEXT
        msg_1.data = json.dumps(payload_1)
        msg_2 = MagicMock()
        msg_2.type = aiohttp.WSMsgType.TEXT
        msg_2.data = json.dumps(payload_2)

        ws = _AsyncIter([msg_1, msg_2])

        callback = AsyncMock(side_effect=[ValueError('boom'), None])
        stream = BinanceUserStream(
            adapter=adapter,
            account_id=_ACCOUNT_ID,
            on_message=callback,
        )
        stream._ws = ws  # type: ignore[assignment]

        await stream._receive_loop()
        assert callback.await_count == 2

    @pytest.mark.asyncio
    async def test_receive_loop_breaks_on_closed_message(self) -> None:
        adapter = _make_adapter()
        close_msg = MagicMock()
        close_msg.type = aiohttp.WSMsgType.CLOSED
        trailing_msg = MagicMock()
        trailing_msg.type = aiohttp.WSMsgType.TEXT
        trailing_msg.data = json.dumps({'e': 'should-not-reach'})

        ws = _AsyncIter([close_msg, trailing_msg])

        callback = AsyncMock()
        stream = BinanceUserStream(
            adapter=adapter,
            account_id=_ACCOUNT_ID,
            on_message=callback,
        )
        stream._ws = ws  # type: ignore[assignment]

        await stream._receive_loop()
        callback.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_receive_loop_breaks_on_error_message(self) -> None:
        adapter = _make_adapter()
        error_msg = MagicMock()
        error_msg.type = aiohttp.WSMsgType.ERROR

        ws = _AsyncIter([error_msg])

        callback = AsyncMock()
        stream = BinanceUserStream(
            adapter=adapter,
            account_id=_ACCOUNT_ID,
            on_message=callback,
        )
        stream._ws = ws  # type: ignore[assignment]

        await stream._receive_loop()
        callback.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_keepalive_loop_calls_adapter(self) -> None:

        adapter = _make_adapter()
        stream = BinanceUserStream(
            adapter=adapter,
            account_id=_ACCOUNT_ID,
            keepalive_interval_seconds=0,
        )
        stream._listen_key = 'listen-key'

        with patch('praxis.infrastructure.binance_ws.asyncio.sleep', new_callable=AsyncMock) as mock_sleep:
            mock_sleep.side_effect = [None, asyncio.CancelledError]
            with pytest.raises(asyncio.CancelledError):
                await stream._keepalive_loop()

        adapter._keepalive_listen_key.assert_awaited_once_with(_ACCOUNT_ID, 'listen-key')

    @pytest.mark.asyncio
    async def test_connect_build_ws_url_failure_closes_listen_key(self) -> None:

        adapter = _make_adapter('ftp://bad-scheme.example.com')
        session = MagicMock()
        adapter._ensure_session.return_value = session

        stream = BinanceUserStream(adapter=adapter, account_id=_ACCOUNT_ID)
        with pytest.raises(ValueError, match='Unsupported base URL scheme'):
            await stream.initiate_connection()

        adapter._close_listen_key.assert_awaited_once_with(_ACCOUNT_ID, 'listen-key')

    @pytest.mark.asyncio
    async def test_keepalive_loop_logs_and_continues_on_failure(self) -> None:

        adapter = _make_adapter()
        adapter._keepalive_listen_key = AsyncMock(
            side_effect=[VenueError('boom'), None],
        )
        stream = BinanceUserStream(
            adapter=adapter,
            account_id=_ACCOUNT_ID,
            keepalive_interval_seconds=0,
        )
        stream._listen_key = 'listen-key'

        with patch('praxis.infrastructure.binance_ws.asyncio.sleep', new_callable=AsyncMock) as mock_sleep:
            mock_sleep.side_effect = [None, None, asyncio.CancelledError]
            with pytest.raises(asyncio.CancelledError):
                await stream._keepalive_loop()

        assert adapter._keepalive_listen_key.await_count == 2

    @pytest.mark.asyncio
    async def test_auto_reconnect_reconnects_after_ws_disconnect(self) -> None:
        adapter = _make_adapter()
        callback = AsyncMock()
        stream = BinanceUserStream(
            adapter=adapter,
            account_id=_ACCOUNT_ID,
            on_message=callback,
            reconnect_base_delay=1.0,
        )

        receive_mock = AsyncMock(side_effect=[None, asyncio.CancelledError])

        with (
            patch.object(stream, '_receive_loop', receive_mock),
            patch.object(
                stream, '_clean_setup_connection', new_callable=AsyncMock,
            ) as mock_setup,
            patch('praxis.infrastructure.binance_ws.asyncio.sleep', new_callable=AsyncMock),
            patch('praxis.infrastructure.binance_ws.random.random', return_value=0.5),
            pytest.raises(asyncio.CancelledError),
        ):
            await stream._auto_reconnect()

        mock_setup.assert_awaited_once()
        assert receive_mock.await_count == 2

    @pytest.mark.asyncio
    async def test_auto_reconnect_uses_exponential_backoff(self) -> None:
        adapter = _make_adapter()
        callback = AsyncMock()
        stream = BinanceUserStream(
            adapter=adapter,
            account_id=_ACCOUNT_ID,
            on_message=callback,
            reconnect_base_delay=1.0,
            reconnect_max_delay=60.0,
        )

        receive_mock = AsyncMock(side_effect=[None, asyncio.CancelledError])
        setup_mock = AsyncMock(side_effect=[
            VenueError('fail-1'),
            VenueError('fail-2'),
            None,
        ])

        with (
            patch.object(stream, '_receive_loop', receive_mock),
            patch.object(stream, '_clean_setup_connection', setup_mock),
            patch('praxis.infrastructure.binance_ws.asyncio.sleep', new_callable=AsyncMock) as mock_sleep,
            patch('praxis.infrastructure.binance_ws.random.random', return_value=0.5),
            pytest.raises(asyncio.CancelledError),
        ):
            await stream._auto_reconnect()

        assert mock_sleep.await_count == 3
        delays = [call.args[0] for call in mock_sleep.call_args_list]
        assert delays == [0.75, 1.5, 3.0]

    @pytest.mark.asyncio
    async def test_auto_reconnect_resets_attempts_after_successful_reconnect(self) -> None:
        adapter = _make_adapter()
        callback = AsyncMock()
        stream = BinanceUserStream(
            adapter=adapter,
            account_id=_ACCOUNT_ID,
            on_message=callback,
            reconnect_base_delay=1.0,
        )

        receive_mock = AsyncMock(side_effect=[None, None, asyncio.CancelledError])
        setup_mock = AsyncMock()

        with (
            patch.object(stream, '_receive_loop', receive_mock),
            patch.object(stream, '_clean_setup_connection', setup_mock),
            patch('praxis.infrastructure.binance_ws.asyncio.sleep', new_callable=AsyncMock) as mock_sleep,
            patch('praxis.infrastructure.binance_ws.random.random', return_value=0.5),
            pytest.raises(asyncio.CancelledError),
        ):
            await stream._auto_reconnect()

        assert mock_sleep.await_count == 2
        delays = [call.args[0] for call in mock_sleep.call_args_list]
        assert delays[0] == delays[1]

    @pytest.mark.asyncio
    async def test_auto_reconnect_exits_on_cancel_during_backoff(self) -> None:
        adapter = _make_adapter()
        callback = AsyncMock()
        stream = BinanceUserStream(
            adapter=adapter,
            account_id=_ACCOUNT_ID,
            on_message=callback,
            reconnect_base_delay=1.0,
        )

        receive_mock = AsyncMock(return_value=None)
        sleep_mock = AsyncMock(side_effect=asyncio.CancelledError)

        with (
            patch.object(stream, '_receive_loop', receive_mock),
            patch('praxis.infrastructure.binance_ws.asyncio.sleep', sleep_mock),
            patch('praxis.infrastructure.binance_ws.random.random', return_value=0.5),
            pytest.raises(asyncio.CancelledError),
        ):
            await stream._auto_reconnect()

        receive_mock.assert_awaited_once()
