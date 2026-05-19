'''Tests for launcher `TRADE_MODE` env-var URL routing (MAJOR-001).

`TRADE_MODE=paper` resolves to the in-code Binance Spot testnet URLs
plus `market_data_testnet=True`; `TRADE_MODE=live` resolves to the
mainnet URLs plus `market_data_testnet=False`. Anything else raises
`RuntimeError` so a misconfigured deployment cannot reach the venue.
'''

from __future__ import annotations

import pytest

from praxis.infrastructure.binance_urls import (
    MAINNET_REST_URL,
    MAINNET_WS_API_URL,
    MAINNET_WS_URL,
    TESTNET_REST_URL,
    TESTNET_WS_API_URL,
    TESTNET_WS_URL,
)
from praxis.launcher import _resolve_trade_mode


class TestResolveTradeMode:

    def test_paper_returns_testnet_urls_and_testnet_flag(self) -> None:
        rest, ws, ws_api, testnet = _resolve_trade_mode({'TRADE_MODE': 'paper'})

        assert rest == TESTNET_REST_URL
        assert ws == TESTNET_WS_URL
        assert ws_api == TESTNET_WS_API_URL
        assert testnet is True

    def test_live_returns_mainnet_urls_and_testnet_flag_false(self) -> None:
        rest, ws, ws_api, testnet = _resolve_trade_mode({'TRADE_MODE': 'live'})

        assert rest == MAINNET_REST_URL
        assert ws == MAINNET_WS_URL
        assert ws_api == MAINNET_WS_API_URL
        assert testnet is False

    def test_paper_is_case_insensitive_and_strips_whitespace(self) -> None:
        rest, ws, ws_api, testnet = _resolve_trade_mode({'TRADE_MODE': '  PAPER  '})

        assert rest == TESTNET_REST_URL
        assert ws == TESTNET_WS_URL
        assert ws_api == TESTNET_WS_API_URL
        assert testnet is True

    def test_live_is_case_insensitive(self) -> None:
        rest, ws, ws_api, testnet = _resolve_trade_mode({'TRADE_MODE': 'Live'})

        assert rest == MAINNET_REST_URL
        assert ws == MAINNET_WS_URL
        assert ws_api == MAINNET_WS_API_URL
        assert testnet is False

    def test_unknown_value_rejected(self) -> None:
        with pytest.raises(RuntimeError, match='TRADE_MODE must be one of'):
            _resolve_trade_mode({'TRADE_MODE': 'staging'})

    def test_empty_value_rejected(self) -> None:
        with pytest.raises(RuntimeError, match='TRADE_MODE must be one of'):
            _resolve_trade_mode({'TRADE_MODE': ''})


class TestResolveTradeModeBinsim:

    def test_paper_with_binsim_url_returns_derived_urls_and_testnet_flag(self) -> None:
        rest, ws, ws_api, testnet = _resolve_trade_mode({
            'TRADE_MODE': 'paper',
            'BINSIM_URL': 'http://binsim:8081',
        })

        assert rest == 'http://binsim:8081'
        assert ws == 'ws://binsim:8081'
        assert ws_api == 'ws://binsim:8081/ws-api/v3'
        assert testnet is True

    def test_paper_with_https_binsim_url_uses_wss(self) -> None:
        rest, ws, ws_api, testnet = _resolve_trade_mode({
            'TRADE_MODE': 'paper',
            'BINSIM_URL': 'https://binsim.internal:8443',
        })

        assert rest == 'https://binsim.internal:8443'
        assert ws == 'wss://binsim.internal:8443'
        assert ws_api == 'wss://binsim.internal:8443/ws-api/v3'
        assert testnet is True

    def test_paper_with_empty_binsim_url_falls_back_to_testnet(self) -> None:
        rest, ws, ws_api, _testnet = _resolve_trade_mode({
            'TRADE_MODE': 'paper',
            'BINSIM_URL': '',
        })

        assert rest == TESTNET_REST_URL
        assert ws == TESTNET_WS_URL
        assert ws_api == TESTNET_WS_API_URL

    def test_paper_with_whitespace_only_binsim_url_falls_back_to_testnet(self) -> None:
        rest, _, _, _ = _resolve_trade_mode({
            'TRADE_MODE': 'paper',
            'BINSIM_URL': '   ',
        })

        assert rest == TESTNET_REST_URL

    def test_paper_with_binsim_url_strips_trailing_path(self) -> None:
        rest, ws, ws_api, _ = _resolve_trade_mode({
            'TRADE_MODE': 'paper',
            'BINSIM_URL': 'http://binsim:8081/api/v3',
        })

        assert rest == 'http://binsim:8081'
        assert ws == 'ws://binsim:8081'
        assert ws_api == 'ws://binsim:8081/ws-api/v3'

    def test_live_with_binsim_url_set_raises(self) -> None:
        with pytest.raises(RuntimeError, match='BINSIM_URL must not be set when TRADE_MODE=live'):
            _resolve_trade_mode({
                'TRADE_MODE': 'live',
                'BINSIM_URL': 'http://binsim:8081',
            })

    def test_binsim_url_with_bad_scheme_raises(self) -> None:
        with pytest.raises(RuntimeError, match='BINSIM_URL must use http or https scheme'):
            _resolve_trade_mode({
                'TRADE_MODE': 'paper',
                'BINSIM_URL': 'ws://binsim:8081',
            })

    def test_binsim_url_without_host_raises(self) -> None:
        with pytest.raises(RuntimeError, match='BINSIM_URL must include a host'):
            _resolve_trade_mode({
                'TRADE_MODE': 'paper',
                'BINSIM_URL': 'http://',
            })
