'''Tests for praxis.binsim.__main__._parse_env.'''

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pytest

from praxis.binsim.__main__ import _parse_env


_BASE_ENV = {
    'BINSIM_DEPTH_TOKEN': 'token-1',
    'BINSIM_STATE_DIR': '/var/lib/binsim',
}


def test_parses_minimum_required_env_with_defaults() -> None:

    config = _parse_env(dict(_BASE_ENV))

    assert config.depth_token == 'token-1'  # noqa: S105 — test fixture, not a real credential
    assert config.state_dir == Path('/var/lib/binsim')
    assert config.host == '0.0.0.0'  # noqa: S104 — bind-all is the documented default
    assert config.port == 8081
    assert config.depth_url == 'https://binance-spot-depth20-1000ms.onrender.com/top20'
    assert config.staleness_threshold_ms == 5000
    assert config.poll_interval_ms == 1000
    assert config.min_top20_depth_btc == Decimal('0.05')
    assert config.max_stuck_update_id_polls == 5


def test_parses_full_env_overrides() -> None:

    env = {
        **_BASE_ENV,
        'BINSIM_HOST': '127.0.0.1',
        'BINSIM_PORT': '9000',
        'BINSIM_DEPTH_URL': 'https://example.com/top20',
        'BINSIM_STALENESS_MS': '7500',
        'BINSIM_POLL_INTERVAL_MS': '500',
        'BINSIM_MIN_TOP20_DEPTH_BTC': '0.25',
        'BINSIM_MAX_STUCK_UPDATE_ID_POLLS': '10',
    }

    config = _parse_env(env)

    assert config.host == '127.0.0.1'
    assert config.port == 9000
    assert config.depth_url == 'https://example.com/top20'
    assert config.staleness_threshold_ms == 7500
    assert config.poll_interval_ms == 500
    assert config.min_top20_depth_btc == Decimal('0.25')
    assert config.max_stuck_update_id_polls == 10


@pytest.mark.parametrize('missing_var', ['BINSIM_DEPTH_TOKEN', 'BINSIM_STATE_DIR'])
def test_missing_required_env_raises(missing_var: str) -> None:

    env = {k: v for k, v in _BASE_ENV.items() if k != missing_var}

    with pytest.raises(RuntimeError, match=f'{missing_var} is required'):
        _parse_env(env)


@pytest.mark.parametrize('empty_value', ['', '   '])
def test_empty_required_env_treated_as_missing(empty_value: str) -> None:

    env = {**_BASE_ENV, 'BINSIM_DEPTH_TOKEN': empty_value}

    with pytest.raises(RuntimeError, match='BINSIM_DEPTH_TOKEN is required'):
        _parse_env(env)


@pytest.mark.parametrize(
    'var,bad_value',
    [
        ('BINSIM_PORT', 'not-a-number'),
        ('BINSIM_STALENESS_MS', 'abc'),
        ('BINSIM_POLL_INTERVAL_MS', '1.5'),
    ],
)
def test_invalid_int_env_raises(var: str, bad_value: str) -> None:

    env = {**_BASE_ENV, var: bad_value}

    with pytest.raises(RuntimeError, match=f'{var} must be an integer'):
        _parse_env(env)


def test_blank_int_env_falls_back_to_default() -> None:

    env = {**_BASE_ENV, 'BINSIM_PORT': '   '}

    config = _parse_env(env)
    assert config.port == 8081


def test_empty_optional_string_falls_back_to_default() -> None:

    env = {**_BASE_ENV, 'BINSIM_HOST': '   ', 'BINSIM_DEPTH_URL': '  '}

    config = _parse_env(env)
    assert config.host == '0.0.0.0'  # noqa: S104 — bind-all is the documented default
    assert config.depth_url == 'https://binance-spot-depth20-1000ms.onrender.com/top20'


@pytest.mark.parametrize(
    'raw',
    ['not-a-decimal', 'NaN', 'Infinity', '-Infinity', '0', '-0.1', '-1'],
)
def test_invalid_min_top20_depth_btc_raises(raw: str) -> None:

    env = {**_BASE_ENV, 'BINSIM_MIN_TOP20_DEPTH_BTC': raw}

    with pytest.raises(RuntimeError, match='BINSIM_MIN_TOP20_DEPTH_BTC'):
        _parse_env(env)


def test_blank_min_top20_depth_btc_falls_back_to_default() -> None:

    env = {**_BASE_ENV, 'BINSIM_MIN_TOP20_DEPTH_BTC': '   '}

    config = _parse_env(env)

    assert config.min_top20_depth_btc == Decimal('0.05')


@pytest.mark.parametrize('raw', ['0', '-1', '1', 'not-int', '1.5'])
def test_invalid_max_stuck_update_id_polls_raises(raw: str) -> None:
    '''Pin: `1` is invalid too because the meaningful minimum is 2.

    The env parser delegates to `_parse_int_env(..., min_value=2)`,
    so `1` is rejected at parse time with the same RuntimeError
    that catches `0` / `-1` / non-int / float.
    '''

    env = {**_BASE_ENV, 'BINSIM_MAX_STUCK_UPDATE_ID_POLLS': raw}

    with pytest.raises(RuntimeError, match='BINSIM_MAX_STUCK_UPDATE_ID_POLLS'):
        _parse_env(env)


def test_register_subcommand_prints_api_key(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from praxis.binsim.__main__ import main

    monkeypatch.setenv('BINSIM_STATE_DIR', str(tmp_path))
    main(['register', '--account-id', 'acc-1', '--initial-usdt', '10000'])

    captured = capsys.readouterr()
    api_key = captured.out.strip()
    assert len(api_key) == 64
    assert all(c in '0123456789abcdef' for c in api_key)


def test_register_subcommand_requires_state_dir(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from praxis.binsim.__main__ import main

    monkeypatch.delenv('BINSIM_STATE_DIR', raising=False)
    _ = tmp_path

    with pytest.raises(SystemExit, match='BINSIM_STATE_DIR is required'):
        main(['register', '--account-id', 'acc-1', '--initial-usdt', '1'])


def test_register_subcommand_rejects_bad_decimal(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from praxis.binsim.__main__ import main

    monkeypatch.setenv('BINSIM_STATE_DIR', str(tmp_path))

    with pytest.raises(SystemExit, match='--initial-usdt must be a valid decimal'):
        main(['register', '--account-id', 'acc-1', '--initial-usdt', 'not-a-number'])


@pytest.mark.parametrize('var', ['BINSIM_STALENESS_MS', 'BINSIM_POLL_INTERVAL_MS'])
def test_zero_strict_positive_int_env_raises(var: str) -> None:
    env = {**_BASE_ENV, var: '0'}

    with pytest.raises(RuntimeError, match=f'{var} must be >= 1'):
        _parse_env(env)


@pytest.mark.parametrize('var', ['BINSIM_STALENESS_MS', 'BINSIM_POLL_INTERVAL_MS'])
def test_negative_strict_positive_int_env_raises(var: str) -> None:
    env = {**_BASE_ENV, var: '-1'}

    with pytest.raises(RuntimeError, match=f'{var} must be >= 1'):
        _parse_env(env)


def test_negative_port_env_raises() -> None:
    env = {**_BASE_ENV, 'BINSIM_PORT': '-1'}

    with pytest.raises(RuntimeError, match='BINSIM_PORT must be >= 0'):
        _parse_env(env)


def test_oversized_port_env_raises() -> None:
    env = {**_BASE_ENV, 'BINSIM_PORT': '65536'}

    with pytest.raises(RuntimeError, match='BINSIM_PORT must be <= 65535'):
        _parse_env(env)


def test_zero_port_env_accepted_for_ephemeral_binding() -> None:
    env = {**_BASE_ENV, 'BINSIM_PORT': '0'}

    config = _parse_env(env)
    assert config.port == 0
