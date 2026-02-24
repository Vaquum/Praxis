'''Shared constants, auth helpers, and skip markers for testnet tests.

Usage:
    # Option A: .env file in repo root (gitignored)
    echo "BINANCE_TESTNET_API_KEY='your_key'" >> .env
    echo "BINANCE_TESTNET_API_SECRET='your_secret'" >> .env

    # Option B: shell exports
    export BINANCE_TESTNET_API_KEY='your_key'
    export BINANCE_TESTNET_API_SECRET='your_secret'

    python -m pytest tests/testnet/ -v

Requires: uv pip install aiohttp websockets pytest-asyncio python-dotenv
'''

from __future__ import annotations

import hashlib
import hmac
import os
import time
from urllib.parse import urlencode

import aiohttp
import pytest
from dotenv import load_dotenv

load_dotenv()

REST_BASE = 'https://testnet.binance.vision'
WS_BASE = 'wss://stream.testnet.binance.vision'
SYMBOL = 'BTCUSDT'

HTTP_OK = 200
MAX_CLOCK_SKEW_MS = 5000
WS_CLOSE_TIMEOUT = 5
WS_RECV_TIMEOUT = 10
RATE_LIMIT_HEADER = 'X-MBX-USED-WEIGHT-1M'
API_KEY_HEADER = 'X-MBX-APIKEY'
MIN_ORDER_QUOTE_QTY = '11'
SESSION_TIMEOUT = aiohttp.ClientTimeout(total=30)


def _testnet_reachable() -> bool:

    '''Compute whether the Binance Spot testnet is reachable from this host.

    Returns:
        bool: True if GET /api/v3/ping returns 200
    '''

    import urllib.error
    import urllib.request

    try:
        with urllib.request.urlopen(  # noqa: S310
            f"{REST_BASE}/api/v3/ping", timeout=5
        ) as resp:
            return resp.status == HTTP_OK
    except (urllib.error.URLError, OSError):
        return False


pytestmark = pytest.mark.skipif(
    not _testnet_reachable(),
    reason='Binance testnet unreachable (geo-blocked or offline)',
)


def _api_key() -> str:

    '''Fetch the API key from the environment.

    Returns:
        str: Value of BINANCE_TESTNET_API_KEY

    Raises:
        KeyError: If BINANCE_TESTNET_API_KEY is not set
    '''

    return os.environ['BINANCE_TESTNET_API_KEY']


def _api_secret() -> str:

    '''Fetch the API secret from the environment.

    Returns:
        str: Value of BINANCE_TESTNET_API_SECRET

    Raises:
        KeyError: If BINANCE_TESTNET_API_SECRET is not set
    '''

    return os.environ['BINANCE_TESTNET_API_SECRET']


def _sign(query_string: str, secret: str) -> str:

    '''Compute HMAC-SHA256 signature for Binance authenticated endpoints.

    Args:
        query_string (str): URL-encoded query string to sign
        secret (str): API secret used as HMAC key

    Returns:
        str: Hex-encoded HMAC-SHA256 signature
    '''

    return hmac.new(secret.encode(), query_string.encode(), hashlib.sha256).hexdigest()


def auth_headers() -> dict[str, str]:

    '''Compute HTTP headers required for authenticated REST calls.

    Returns:
        dict[str, str]: Headers with API key set
    '''

    return {API_KEY_HEADER: _api_key()}


def signed_params(**extra: str) -> dict[str, str]:

    '''Compute signed query parameters for authenticated REST endpoints.

    Args:
        **extra (str): Additional key-value pairs to include before signing

    Returns:
        dict[str, str]: Parameters including timestamp and signature
    '''

    params = {'timestamp': str(int(time.time() * 1000)), **extra}
    query = urlencode(params)
    params['signature'] = _sign(query, _api_secret())
    return params


skip_no_creds = pytest.mark.skipif(
    not os.environ.get('BINANCE_TESTNET_API_KEY')
    or not os.environ.get('BINANCE_TESTNET_API_SECRET'),
    reason='BINANCE_TESTNET_API_KEY / BINANCE_TESTNET_API_SECRET not set',
)
