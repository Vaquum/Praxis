'''
Tests for praxis.infrastructure.binance_ws.
'''

from __future__ import annotations

import asyncio
import contextlib
import hashlib
import hmac
import json
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import aiohttp

from praxis.infrastructure.binance_ws import BinanceUserStream
from praxis.infrastructure.venue_adapter import AuthenticationError, VenueError


_ACCOUNT_ID = 'test-account'
_API_KEY = 'k'
_API_SECRET = 's'  # noqa: S105 - test fixture, not a real secret
_FIXTURE_API_SECRET = 'SECRET'  # noqa: S105 - test fixture, not a real secret
_WS_API_URL = 'wss://ws-api.testnet.binance.vision/ws-api/v3'


def _make_adapter(
    ws_api_url: str = _WS_API_URL,
    api_key: str = _API_KEY,
    api_secret: str = _API_SECRET,
) -> Any:

    '''
    Create a mock BinanceAdapter exposing the surface BinanceUserStream
    reads: `_ws_api_url`, `_get_credentials`, `_ensure_session`.

    Args:
        ws_api_url (str): WS-API base URL
        api_key (str): API key returned by the mocked `_get_credentials`
            for `_ACCOUNT_ID`
        api_secret (str): API secret returned by the mocked
            `_get_credentials` for `_ACCOUNT_ID`

    Returns:
        Any: Mock adapter
    '''

    adapter = MagicMock()
    adapter._ws_api_url = ws_api_url
    adapter._get_credentials = MagicMock(return_value=(api_key, api_secret))
    adapter._ensure_session = AsyncMock()
    return adapter


def _make_ack_msg(
    status: int = 200,
    subscription_id: int = 0,
) -> MagicMock:

    '''
    Build a mock WS-API subscribe-ack TEXT frame.

    Args:
        status (int): WS-API ack status code
        subscription_id (int): subscriptionId to embed in `result`

    Returns:
        MagicMock: Mock aiohttp WSMessage
    '''

    msg = MagicMock()
    msg.type = aiohttp.WSMsgType.TEXT
    msg.data = json.dumps({
        'id': 'req-1',
        'status': status,
        'result': {'subscriptionId': subscription_id},
    })
    return msg


def _make_session_with_ack(
    ws_mock: AsyncMock,
    ack_msg: MagicMock | None = None,
) -> MagicMock:

    '''
    Build a mock aiohttp ClientSession whose `ws_connect` returns the
    given ws and whose ws.receive returns the given ack frame.

    Args:
        ws_mock (AsyncMock): Mock WebSocket to return from `ws_connect`
        ack_msg (MagicMock | None): Ack frame to deliver via `receive`;
            defaults to a 200 / subscriptionId=0 ack

    Returns:
        MagicMock: Mock session
    '''

    if ack_msg is None:
        ack_msg = _make_ack_msg()
    ws_mock.receive = AsyncMock(return_value=ack_msg)
    ws_mock.send_str = AsyncMock()
    ws_mock.close = AsyncMock()
    session = MagicMock()
    session.ws_connect = AsyncMock(return_value=ws_mock)
    return session


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


class TestSetupConnection:

    @pytest.mark.asyncio
    async def test_initiate_connection_subscribes_and_stores_ws(self) -> None:
        adapter = _make_adapter()
        ws = AsyncMock()
        ws.closed = False
        session = _make_session_with_ack(ws, _make_ack_msg(subscription_id=42))
        adapter._ensure_session.return_value = session

        stream = BinanceUserStream(adapter=adapter, account_id=_ACCOUNT_ID)
        await stream.initiate_connection()

        session.ws_connect.assert_awaited_once_with(_WS_API_URL)
        ws.send_str.assert_awaited_once()
        assert stream.websocket is ws
        assert stream.subscription_id == 42

    @pytest.mark.asyncio
    async def test_initiate_connection_skips_when_already_connected(self) -> None:
        adapter = _make_adapter()
        ws = AsyncMock()
        ws.closed = False
        session = _make_session_with_ack(ws)
        adapter._ensure_session.return_value = session

        stream = BinanceUserStream(adapter=adapter, account_id=_ACCOUNT_ID)
        await stream.initiate_connection()
        session.ws_connect.reset_mock()

        await stream.initiate_connection()

        session.ws_connect.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_initiate_connection_skips_when_reconnect_task_running(self) -> None:
        adapter = _make_adapter()
        stream = BinanceUserStream(adapter=adapter, account_id=_ACCOUNT_ID)
        stream._reconnect_task = asyncio.create_task(asyncio.sleep(999))

        await stream.initiate_connection()

        adapter._ensure_session.assert_not_awaited()

        stream._reconnect_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await stream._reconnect_task

    @pytest.mark.asyncio
    async def test_initiate_connection_replaces_stale_ws(self) -> None:
        adapter = _make_adapter()
        ws_first = AsyncMock()
        ws_first.closed = False
        ws_first.send_str = AsyncMock()
        ws_first.close = AsyncMock()
        ws_first.receive = AsyncMock(return_value=_make_ack_msg(subscription_id=1))

        session = MagicMock()
        adapter._ensure_session.return_value = session
        session.ws_connect = AsyncMock(return_value=ws_first)

        stream = BinanceUserStream(adapter=adapter, account_id=_ACCOUNT_ID)
        await stream.initiate_connection()
        assert stream.subscription_id == 1

        ws_first.closed = True
        ws_second = AsyncMock()
        ws_second.closed = False
        ws_second.send_str = AsyncMock()
        ws_second.close = AsyncMock()
        ws_second.receive = AsyncMock(return_value=_make_ack_msg(subscription_id=2))
        session.ws_connect = AsyncMock(return_value=ws_second)

        await stream.initiate_connection()

        ws_first.close.assert_awaited()
        assert stream.websocket is ws_second
        assert stream.subscription_id == 2

    @pytest.mark.asyncio
    async def test_invalid_ws_api_scheme_raises(self) -> None:
        adapter = _make_adapter(ws_api_url='ftp://bad.example.com')
        stream = BinanceUserStream(adapter=adapter, account_id=_ACCOUNT_ID)
        with pytest.raises(ValueError, match='Unsupported WS-API URL scheme'):
            await stream.initiate_connection()

    @pytest.mark.asyncio
    async def test_ws_scheme_rejected_without_binsim_url_env(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.delenv('BINSIM_URL', raising=False)
        adapter = _make_adapter(ws_api_url='ws://binsim:8081/ws-api/v3')
        stream = BinanceUserStream(adapter=adapter, account_id=_ACCOUNT_ID)
        with pytest.raises(ValueError, match='Unsupported WS-API URL scheme'):
            await stream.initiate_connection()

    @pytest.mark.asyncio
    async def test_ws_scheme_accepted_when_binsim_url_env_is_set(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setenv('BINSIM_URL', 'http://binsim:8081')
        adapter = _make_adapter(ws_api_url='ws://binsim:8081/ws-api/v3')
        ws = AsyncMock()
        adapter._ensure_session = AsyncMock(return_value=_make_session_with_ack(ws))

        stream = BinanceUserStream(adapter=adapter, account_id=_ACCOUNT_ID)
        await stream.initiate_connection()

        assert stream.websocket is ws

    @pytest.mark.asyncio
    async def test_missing_credentials_raises_authentication_error(self) -> None:
        adapter = MagicMock()
        adapter._ws_api_url = _WS_API_URL
        adapter._ensure_session = AsyncMock()
        adapter._get_credentials = MagicMock(
            side_effect=AuthenticationError(
                f"No credentials registered for account '{_ACCOUNT_ID}'",
            ),
        )

        stream = BinanceUserStream(adapter=adapter, account_id=_ACCOUNT_ID)
        with pytest.raises(AuthenticationError, match='No credentials registered'):
            await stream.initiate_connection()

    @pytest.mark.asyncio
    async def test_subscribe_failure_closes_ws_and_propagates(self) -> None:
        adapter = _make_adapter()
        ws = AsyncMock()
        ws.closed = False
        ws.send_str = AsyncMock()
        ws.close = AsyncMock()
        ws.receive = AsyncMock(return_value=_make_ack_msg(status=400))
        session = MagicMock()
        session.ws_connect = AsyncMock(return_value=ws)
        adapter._ensure_session.return_value = session

        stream = BinanceUserStream(adapter=adapter, account_id=_ACCOUNT_ID)
        with pytest.raises(VenueError, match='WS-API subscribe failed'):
            await stream.initiate_connection()

        ws.close.assert_awaited()
        assert stream.websocket is None

    @pytest.mark.asyncio
    async def test_ws_connect_failure_propagates(self) -> None:
        adapter = _make_adapter()
        session = MagicMock()
        session.ws_connect = AsyncMock(side_effect=aiohttp.ClientError('boom'))
        adapter._ensure_session.return_value = session

        stream = BinanceUserStream(adapter=adapter, account_id=_ACCOUNT_ID)
        with pytest.raises(aiohttp.ClientError, match='boom'):
            await stream.initiate_connection()


class TestSubscribeFraming:

    @pytest.mark.asyncio
    async def test_subscribe_frame_uses_signed_params(self) -> None:
        adapter = _make_adapter(api_key='APIKEY', api_secret=_FIXTURE_API_SECRET)
        ws = AsyncMock()
        ws.closed = False
        ws.send_str = AsyncMock()
        ws.close = AsyncMock()
        ws.receive = AsyncMock(return_value=_make_ack_msg())
        session = MagicMock()
        session.ws_connect = AsyncMock(return_value=ws)
        adapter._ensure_session.return_value = session

        stream = BinanceUserStream(adapter=adapter, account_id=_ACCOUNT_ID)
        await stream.initiate_connection()

        ws.send_str.assert_awaited_once()
        sent_payload = json.loads(ws.send_str.await_args.args[0])
        assert sent_payload['method'] == 'userDataStream.subscribe.signature'
        params = sent_payload['params']
        assert params['apiKey'] == 'APIKEY'
        assert params['recvWindow'] == 5000
        assert isinstance(params['timestamp'], int)

        signing_params = {k: v for k, v in params.items() if k != 'signature'}
        qs = '&'.join(f'{k}={signing_params[k]}' for k in sorted(signing_params))
        expected = hmac.new(
            _FIXTURE_API_SECRET.encode(), qs.encode(), hashlib.sha256,
        ).hexdigest()
        assert params['signature'] == expected

    @pytest.mark.asyncio
    async def test_subscribe_ack_timeout_raises_timeout_error(self) -> None:
        adapter = _make_adapter()
        ws = AsyncMock()
        ws.closed = False
        ws.send_str = AsyncMock()
        ws.close = AsyncMock()
        ws.receive = AsyncMock(side_effect=TimeoutError())
        session = MagicMock()
        session.ws_connect = AsyncMock(return_value=ws)
        adapter._ensure_session.return_value = session

        stream = BinanceUserStream(adapter=adapter, account_id=_ACCOUNT_ID)
        with pytest.raises(TimeoutError, match='WS-API subscribe ack timed out'):
            await stream.initiate_connection()

        ws.close.assert_awaited()

    @pytest.mark.asyncio
    async def test_subscribe_non_text_frame_raises(self) -> None:
        adapter = _make_adapter()
        ws = AsyncMock()
        ws.closed = False
        ws.send_str = AsyncMock()
        ws.close = AsyncMock()
        non_text = MagicMock()
        non_text.type = aiohttp.WSMsgType.BINARY
        ws.receive = AsyncMock(return_value=non_text)
        session = MagicMock()
        session.ws_connect = AsyncMock(return_value=ws)
        adapter._ensure_session.return_value = session

        stream = BinanceUserStream(adapter=adapter, account_id=_ACCOUNT_ID)
        with pytest.raises(VenueError, match='non-text frame'):
            await stream.initiate_connection()

    @pytest.mark.asyncio
    async def test_subscribe_non_json_frame_raises(self) -> None:
        adapter = _make_adapter()
        ws = AsyncMock()
        ws.closed = False
        ws.send_str = AsyncMock()
        ws.close = AsyncMock()
        bad = MagicMock()
        bad.type = aiohttp.WSMsgType.TEXT
        bad.data = 'not-json'
        ws.receive = AsyncMock(return_value=bad)
        session = MagicMock()
        session.ws_connect = AsyncMock(return_value=ws)
        adapter._ensure_session.return_value = session

        stream = BinanceUserStream(adapter=adapter, account_id=_ACCOUNT_ID)
        with pytest.raises(VenueError, match='non-JSON frame'):
            await stream.initiate_connection()

    @pytest.mark.asyncio
    async def test_subscribe_missing_subscription_id_raises(self) -> None:
        adapter = _make_adapter()
        ws = AsyncMock()
        ws.closed = False
        ws.send_str = AsyncMock()
        ws.close = AsyncMock()
        bad_ack = MagicMock()
        bad_ack.type = aiohttp.WSMsgType.TEXT
        bad_ack.data = json.dumps({'id': 'r', 'status': 200, 'result': {}})
        ws.receive = AsyncMock(return_value=bad_ack)
        session = MagicMock()
        session.ws_connect = AsyncMock(return_value=ws)
        adapter._ensure_session.return_value = session

        stream = BinanceUserStream(adapter=adapter, account_id=_ACCOUNT_ID)
        with pytest.raises(VenueError, match='missing subscriptionId'):
            await stream.initiate_connection()

    @pytest.mark.asyncio
    async def test_subscribe_bool_subscription_id_raises(self) -> None:
        adapter = _make_adapter()
        ws = AsyncMock()
        ws.closed = False
        ws.send_str = AsyncMock()
        ws.close = AsyncMock()
        bad_ack = MagicMock()
        bad_ack.type = aiohttp.WSMsgType.TEXT
        bad_ack.data = json.dumps(
            {'id': 'r', 'status': 200, 'result': {'subscriptionId': True}},
        )
        ws.receive = AsyncMock(return_value=bad_ack)
        session = MagicMock()
        session.ws_connect = AsyncMock(return_value=ws)
        adapter._ensure_session.return_value = session

        stream = BinanceUserStream(adapter=adapter, account_id=_ACCOUNT_ID)
        with pytest.raises(VenueError, match='missing subscriptionId'):
            await stream.initiate_connection()


class TestClose:

    @pytest.mark.asyncio
    async def test_close_sends_unsubscribe_and_closes_ws(self) -> None:
        adapter = _make_adapter()
        ws = AsyncMock()
        ws.closed = False
        ws.send_str = AsyncMock()
        ws.close = AsyncMock()
        ws.receive = AsyncMock(return_value=_make_ack_msg(subscription_id=99))
        session = MagicMock()
        session.ws_connect = AsyncMock(return_value=ws)
        adapter._ensure_session.return_value = session

        stream = BinanceUserStream(adapter=adapter, account_id=_ACCOUNT_ID)
        await stream.initiate_connection()

        ws.send_str.reset_mock()
        await stream.close()

        ws.send_str.assert_awaited_once()
        sent = json.loads(ws.send_str.await_args.args[0])
        assert sent['method'] == 'userDataStream.unsubscribe'
        assert sent['params'] == {'subscriptionId': 99}
        ws.close.assert_awaited()
        assert stream.websocket is None
        assert stream.subscription_id is None

    @pytest.mark.asyncio
    async def test_close_handles_no_ws(self) -> None:
        adapter = _make_adapter()
        stream = BinanceUserStream(adapter=adapter, account_id=_ACCOUNT_ID)
        await stream.close()

    @pytest.mark.asyncio
    async def test_close_swallows_unsubscribe_failure(self) -> None:
        adapter = _make_adapter()
        ws = AsyncMock()
        ws.closed = False
        ws.send_str = AsyncMock()
        ws.close = AsyncMock()
        ws.receive = AsyncMock(return_value=_make_ack_msg())
        session = MagicMock()
        session.ws_connect = AsyncMock(return_value=ws)
        adapter._ensure_session.return_value = session

        stream = BinanceUserStream(adapter=adapter, account_id=_ACCOUNT_ID)
        await stream.initiate_connection()
        ws.send_str.side_effect = aiohttp.ClientError('boom')
        await stream.close()

        ws.close.assert_awaited()


class TestAsyncContextManager:

    @pytest.mark.asyncio
    async def test_context_manager_connects_and_closes(self) -> None:
        adapter = _make_adapter()
        ws = AsyncMock()
        ws.closed = False
        ws.send_str = AsyncMock()
        ws.close = AsyncMock()
        ws.receive = AsyncMock(return_value=_make_ack_msg(subscription_id=7))
        session = MagicMock()
        session.ws_connect = AsyncMock(return_value=ws)
        adapter._ensure_session.return_value = session

        async with BinanceUserStream(
            adapter=adapter, account_id=_ACCOUNT_ID,
        ) as stream:
            assert stream.subscription_id == 7

        ws.close.assert_awaited()


class TestReceiveLoop:

    @pytest.mark.asyncio
    async def test_initiate_connection_with_on_message_starts_reconnect_task(
        self,
    ) -> None:
        adapter = _make_adapter()
        ws = AsyncMock()
        ws.closed = False
        ws.send_str = AsyncMock()
        ws.close = AsyncMock()
        ws.receive = AsyncMock(return_value=_make_ack_msg())
        ws.__aiter__ = MagicMock(return_value=_AsyncIter([]))
        session = MagicMock()
        session.ws_connect = AsyncMock(return_value=ws)
        adapter._ensure_session.return_value = session

        callback = AsyncMock()
        stream = BinanceUserStream(
            adapter=adapter, account_id=_ACCOUNT_ID, on_message=callback,
        )
        await stream.initiate_connection()

        assert stream._reconnect_task is not None
        await stream.close()

    @pytest.mark.asyncio
    async def test_receive_loop_dispatches_event_envelope(self) -> None:
        adapter = _make_adapter()
        event_payload = {'e': 'executionReport', 's': 'BTCUSDT'}
        msg = MagicMock()
        msg.type = aiohttp.WSMsgType.TEXT
        msg.data = json.dumps({'event': event_payload})

        ws = _AsyncIter([msg])
        callback = AsyncMock()
        stream = BinanceUserStream(
            adapter=adapter, account_id=_ACCOUNT_ID, on_message=callback,
        )
        stream._ws = ws  # type: ignore[assignment]

        await stream._receive_loop()
        callback.assert_awaited_once_with(event_payload)

    @pytest.mark.asyncio
    async def test_receive_loop_skips_non_event_frame(self) -> None:
        adapter = _make_adapter()
        msg = MagicMock()
        msg.type = aiohttp.WSMsgType.TEXT
        msg.data = json.dumps({'id': 'r', 'status': 200, 'result': {}})

        ws = _AsyncIter([msg])
        callback = AsyncMock()
        stream = BinanceUserStream(
            adapter=adapter, account_id=_ACCOUNT_ID, on_message=callback,
        )
        stream._ws = ws  # type: ignore[assignment]

        await stream._receive_loop()
        callback.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_receive_loop_skips_non_json_frame(self) -> None:
        adapter = _make_adapter()
        msg = MagicMock()
        msg.type = aiohttp.WSMsgType.TEXT
        msg.data = 'not-json'

        ws = _AsyncIter([msg])
        callback = AsyncMock()
        stream = BinanceUserStream(
            adapter=adapter, account_id=_ACCOUNT_ID, on_message=callback,
        )
        stream._ws = ws  # type: ignore[assignment]

        with patch('praxis.infrastructure.binance_ws._log') as mock_logger:
            await stream._receive_loop()
            mock_logger.warning.assert_called_once()

        callback.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_receive_loop_survives_callback_exception(self) -> None:
        adapter = _make_adapter()
        ev_1 = {'e': 'first'}
        ev_2 = {'e': 'second'}
        msg_1 = MagicMock()
        msg_1.type = aiohttp.WSMsgType.TEXT
        msg_1.data = json.dumps({'event': ev_1})
        msg_2 = MagicMock()
        msg_2.type = aiohttp.WSMsgType.TEXT
        msg_2.data = json.dumps({'event': ev_2})

        ws = _AsyncIter([msg_1, msg_2])
        callback = AsyncMock(side_effect=[ValueError('boom'), None])
        stream = BinanceUserStream(
            adapter=adapter, account_id=_ACCOUNT_ID, on_message=callback,
        )
        stream._ws = ws  # type: ignore[assignment]

        await stream._receive_loop()
        assert callback.await_count == 2

    @pytest.mark.asyncio
    async def test_receive_loop_breaks_on_closed_message(self) -> None:
        adapter = _make_adapter()
        close_msg = MagicMock()
        close_msg.type = aiohttp.WSMsgType.CLOSED
        trailing = MagicMock()
        trailing.type = aiohttp.WSMsgType.TEXT
        trailing.data = json.dumps({'event': {'e': 'should-not-reach'}})

        ws = _AsyncIter([close_msg, trailing])
        callback = AsyncMock()
        stream = BinanceUserStream(
            adapter=adapter, account_id=_ACCOUNT_ID, on_message=callback,
        )
        stream._ws = ws  # type: ignore[assignment]

        await stream._receive_loop()
        callback.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_receive_loop_breaks_on_error_message(self) -> None:
        adapter = _make_adapter()
        err = MagicMock()
        err.type = aiohttp.WSMsgType.ERROR

        ws = _AsyncIter([err])
        callback = AsyncMock()
        stream = BinanceUserStream(
            adapter=adapter, account_id=_ACCOUNT_ID, on_message=callback,
        )
        stream._ws = ws  # type: ignore[assignment]

        await stream._receive_loop()
        callback.assert_not_awaited()


class TestAutoReconnect:

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
    async def test_auto_reconnect_resets_attempts_after_successful_reconnect(
        self,
    ) -> None:
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
