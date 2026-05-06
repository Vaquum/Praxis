from __future__ import annotations

__all__ = [
    'MAINNET_REST_URL',
    'MAINNET_WS_API_URL',
    'MAINNET_WS_URL',
    'TESTNET_REST_URL',
    'TESTNET_WS_API_URL',
    'TESTNET_WS_URL',
]

MAINNET_REST_URL = 'https://api.binance.com'
MAINNET_WS_URL = 'wss://stream.binance.com:9443'
MAINNET_WS_API_URL = 'wss://ws-api.binance.com:443/ws-api/v3'
TESTNET_REST_URL = 'https://testnet.binance.vision'
TESTNET_WS_URL = 'wss://stream.testnet.binance.vision'
TESTNET_WS_API_URL = 'wss://ws-api.testnet.binance.vision/ws-api/v3'
