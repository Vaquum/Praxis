'''Tests for `MarketDataPoller(testnet=...)` (PT-FIX-3).

Pre-fix: `_poll_loop` built `Client(None, None, ping=False)` with no
testnet flag. The default URL is `https://api.binance.com` (mainnet),
so a Praxis instance running paper trades on Binance testnet was
reading klines from mainnet BTCUSDT — separate market with separate
prices. ENTER notional sizing in `_build_enter_context` uses these
prices via the launcher fallback price provider, so reservations were
miscalibrated against the testnet capital pool.

Post-fix: `MarketDataPoller(testnet=True)` forwards `testnet=True` to
the `binance.client.Client` constructor, which routes REST calls to
`testnet.binance.vision`.
'''

from __future__ import annotations

import threading
from unittest.mock import patch

from praxis.market_data_poller import MarketDataPoller


class _SentinelClientError(Exception):
    pass


def _capture_client_kwargs(poller: MarketDataPoller) -> dict[str, object]:
    captured: dict[str, object] = {}

    def fake_client(*_args: object, **kwargs: object) -> object:
        captured.update(kwargs)
        raise _SentinelClientError

    stop_event = threading.Event()
    stop_event.set()

    with patch('praxis.market_data_poller.Client', side_effect=fake_client):
        poller._poll_loop(60, 1, stop_event)

    return captured


def test_default_constructs_client_with_testnet_false() -> None:
    '''Default behavior is mainnet (testnet=False) for backwards compat.'''

    poller = MarketDataPoller()
    captured = _capture_client_kwargs(poller)

    assert captured.get('testnet') is False


def test_testnet_true_forwards_to_client_constructor() -> None:
    '''`testnet=True` is passed through to `binance.client.Client`.'''

    poller = MarketDataPoller(testnet=True)
    captured = _capture_client_kwargs(poller)

    assert captured.get('testnet') is True


def test_testnet_false_explicit_forwards_to_client_constructor() -> None:
    poller = MarketDataPoller(testnet=False)
    captured = _capture_client_kwargs(poller)

    assert captured.get('testnet') is False
