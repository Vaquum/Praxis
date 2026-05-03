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
    MAINNET_WS_URL,
    TESTNET_REST_URL,
    TESTNET_WS_URL,
)
from praxis.launcher import _resolve_trade_mode


class TestResolveTradeMode:

    def test_paper_returns_testnet_urls_and_testnet_flag(self) -> None:
        rest, ws, testnet = _resolve_trade_mode({'TRADE_MODE': 'paper'})

        assert rest == TESTNET_REST_URL
        assert ws == TESTNET_WS_URL
        assert testnet is True

    def test_live_returns_mainnet_urls_and_testnet_flag_false(self) -> None:
        rest, ws, testnet = _resolve_trade_mode({'TRADE_MODE': 'live'})

        assert rest == MAINNET_REST_URL
        assert ws == MAINNET_WS_URL
        assert testnet is False

    def test_paper_is_case_insensitive_and_strips_whitespace(self) -> None:
        rest, ws, testnet = _resolve_trade_mode({'TRADE_MODE': '  PAPER  '})

        assert rest == TESTNET_REST_URL
        assert ws == TESTNET_WS_URL
        assert testnet is True

    def test_live_is_case_insensitive(self) -> None:
        rest, ws, testnet = _resolve_trade_mode({'TRADE_MODE': 'Live'})

        assert rest == MAINNET_REST_URL
        assert ws == MAINNET_WS_URL
        assert testnet is False

    def test_unknown_value_rejected(self) -> None:
        with pytest.raises(RuntimeError, match='TRADE_MODE must be one of'):
            _resolve_trade_mode({'TRADE_MODE': 'staging'})

    def test_empty_value_rejected(self) -> None:
        with pytest.raises(RuntimeError, match='TRADE_MODE must be one of'):
            _resolve_trade_mode({'TRADE_MODE': ''})
