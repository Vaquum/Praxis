'''Verify testnet URL constants are safe.'''

from __future__ import annotations

from tests.testnet.conftest import REST_BASE, WS_BASE, pytestmark

__all__ = ['pytestmark']


def test_testnet_urls() -> None:

    '''Verify URL constants point at testnet, not mainnet.'''

    assert REST_BASE == 'https://testnet.binance.vision'
    assert WS_BASE == 'wss://stream.testnet.binance.vision'
