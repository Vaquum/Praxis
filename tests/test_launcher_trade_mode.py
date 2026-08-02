'''Tests for launcher `TRADE_MODE` env-var URL routing (MAJOR-001).

`TRADE_MODE=paper` resolves to the in-code Binance Spot testnet URLs;
`TRADE_MODE=live` resolves to the mainnet URLs. Anything else raises
`RuntimeError` so a misconfigured deployment cannot reach the venue.

`BINSIM_URL` under `TRADE_MODE=paper` overrides the trading-path URLs
to the in-process binsim instance; binsim is a fully internal venue, so
its orders never reach a real venue.
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
from praxis.core.domain.enums import ExecutionMode
from praxis.launcher import _parse_enabled_modes, _resolve_trade_mode


class TestResolveTradeMode:

    def test_paper_returns_testnet_urls(self) -> None:
        rest, ws, ws_api = _resolve_trade_mode({'TRADE_MODE': 'paper'})

        assert rest == TESTNET_REST_URL
        assert ws == TESTNET_WS_URL
        assert ws_api == TESTNET_WS_API_URL

    def test_live_returns_mainnet_urls(self) -> None:
        rest, ws, ws_api = _resolve_trade_mode({'TRADE_MODE': 'live'})

        assert rest == MAINNET_REST_URL
        assert ws == MAINNET_WS_URL
        assert ws_api == MAINNET_WS_API_URL

    def test_paper_is_case_insensitive_and_strips_whitespace(self) -> None:
        rest, ws, ws_api = _resolve_trade_mode({'TRADE_MODE': '  PAPER  '})

        assert rest == TESTNET_REST_URL
        assert ws == TESTNET_WS_URL
        assert ws_api == TESTNET_WS_API_URL

    def test_live_is_case_insensitive(self) -> None:
        rest, ws, ws_api = _resolve_trade_mode({'TRADE_MODE': 'Live'})

        assert rest == MAINNET_REST_URL
        assert ws == MAINNET_WS_URL
        assert ws_api == MAINNET_WS_API_URL

    def test_unknown_value_rejected(self) -> None:
        with pytest.raises(RuntimeError, match='TRADE_MODE must be one of'):
            _resolve_trade_mode({'TRADE_MODE': 'staging'})

    def test_empty_value_rejected(self) -> None:
        with pytest.raises(RuntimeError, match='TRADE_MODE must be one of'):
            _resolve_trade_mode({'TRADE_MODE': ''})


class TestResolveTradeModeBinsim:

    def test_paper_with_binsim_url_returns_derived_urls(self) -> None:
        rest, ws, ws_api = _resolve_trade_mode({
            'TRADE_MODE': 'paper',
            'BINSIM_URL': 'http://binsim:8081',
        })

        assert rest == 'http://binsim:8081'
        assert ws == 'ws://binsim:8081'
        assert ws_api == 'ws://binsim:8081/ws-api/v3'

    def test_paper_with_https_binsim_url_uses_wss(self) -> None:
        rest, ws, ws_api = _resolve_trade_mode({
            'TRADE_MODE': 'paper',
            'BINSIM_URL': 'https://binsim.internal:8443',
        })

        assert rest == 'https://binsim.internal:8443'
        assert ws == 'wss://binsim.internal:8443'
        assert ws_api == 'wss://binsim.internal:8443/ws-api/v3'

    def test_paper_with_empty_binsim_url_falls_back_to_testnet(self) -> None:
        rest, ws, ws_api = _resolve_trade_mode({
            'TRADE_MODE': 'paper',
            'BINSIM_URL': '',
        })

        assert rest == TESTNET_REST_URL
        assert ws == TESTNET_WS_URL
        assert ws_api == TESTNET_WS_API_URL

    def test_paper_with_whitespace_only_binsim_url_falls_back_to_testnet(self) -> None:
        rest, _, _ = _resolve_trade_mode({
            'TRADE_MODE': 'paper',
            'BINSIM_URL': '   ',
        })

        assert rest == TESTNET_REST_URL

    def test_paper_with_binsim_url_strips_trailing_path(self) -> None:
        rest, ws, ws_api = _resolve_trade_mode({
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
        with pytest.raises(RuntimeError, match='BINSIM_URL must include a hostname'):
            _resolve_trade_mode({
                'TRADE_MODE': 'paper',
                'BINSIM_URL': 'http://',
            })

    def test_binsim_url_with_port_but_no_hostname_raises(self) -> None:
        with pytest.raises(RuntimeError, match='BINSIM_URL must include a hostname'):
            _resolve_trade_mode({
                'TRADE_MODE': 'paper',
                'BINSIM_URL': 'http://:8081',
            })


class TestParseEnabledModes:

    def test_unset_defaults_to_single_shot_only(self) -> None:
        modes = _parse_enabled_modes({}, venue_is_binsim=False)

        assert modes == frozenset({ExecutionMode.SINGLE_SHOT})

    def test_empty_defaults_to_single_shot_only(self) -> None:
        modes = _parse_enabled_modes(
            {'PRAXIS_ENABLED_EXECUTION_MODES': '  '}, venue_is_binsim=False,
        )

        assert modes == frozenset({ExecutionMode.SINGLE_SHOT})

    def test_named_modes_are_enabled_with_single_shot(self) -> None:
        modes = _parse_enabled_modes(
            {'PRAXIS_ENABLED_EXECUTION_MODES': 'TWAP, BRACKET'},
            venue_is_binsim=False,
        )

        assert modes == frozenset({
            ExecutionMode.SINGLE_SHOT,
            ExecutionMode.TWAP,
            ExecutionMode.BRACKET,
        })

    def test_unknown_mode_rejected(self) -> None:
        with pytest.raises(ValueError, match='unknown execution mode'):
            _parse_enabled_modes(
                {'PRAXIS_ENABLED_EXECUTION_MODES': 'TWAP,NOPE'},
                venue_is_binsim=False,
            )

    def test_binsim_rejects_live_only_mode(self) -> None:
        with pytest.raises(ValueError, match='live-only mode BRACKET'):
            _parse_enabled_modes(
                {'PRAXIS_ENABLED_EXECUTION_MODES': 'BRACKET'},
                venue_is_binsim=True,
            )

    def test_binsim_allows_paper_safe_mode(self) -> None:
        modes = _parse_enabled_modes(
            {'PRAXIS_ENABLED_EXECUTION_MODES': 'TWAP'}, venue_is_binsim=True,
        )

        assert modes == frozenset({ExecutionMode.SINGLE_SHOT, ExecutionMode.TWAP})

    def test_testnet_paper_allows_live_only_mode(self) -> None:
        modes = _parse_enabled_modes(
            {'PRAXIS_ENABLED_EXECUTION_MODES': 'BRACKET'}, venue_is_binsim=False,
        )

        assert modes == frozenset({
            ExecutionMode.SINGLE_SHOT, ExecutionMode.BRACKET,
        })
