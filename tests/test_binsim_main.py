'''Tests for praxis.binsim.__main__._parse_env.'''

from __future__ import annotations

from pathlib import Path

import pytest

from praxis.binsim.__main__ import _parse_env


_BASE_ENV = {
    'BINSIM_DEPTH_TOKEN': 'token-1',
    'BINSIM_STATE_DIR': '/var/lib/binsim',
    'BINSIM_API_KEYS': 'apikey-1=acc-1',
}


def test_parses_minimum_required_env_with_defaults() -> None:

    config = _parse_env(dict(_BASE_ENV))

    assert config.depth_token == 'token-1'  # noqa: S105 — test fixture, not a real credential
    assert config.state_dir == Path('/var/lib/binsim')
    assert config.api_keys == {'apikey-1': 'acc-1'}
    assert config.host == '0.0.0.0'  # noqa: S104 — bind-all is the documented default
    assert config.port == 8081
    assert config.depth_url == 'https://binance-spot-depth20-1000ms.onrender.com/top20'
    assert config.staleness_threshold_ms == 5000
    assert config.poll_interval_ms == 1000


def test_parses_full_env_overrides() -> None:

    env = {
        **_BASE_ENV,
        'BINSIM_HOST': '127.0.0.1',
        'BINSIM_PORT': '9000',
        'BINSIM_DEPTH_URL': 'https://example.com/top20',
        'BINSIM_STALENESS_MS': '7500',
        'BINSIM_POLL_INTERVAL_MS': '500',
    }

    config = _parse_env(env)

    assert config.host == '127.0.0.1'
    assert config.port == 9000
    assert config.depth_url == 'https://example.com/top20'
    assert config.staleness_threshold_ms == 7500
    assert config.poll_interval_ms == 500


def test_parses_multiple_api_keys() -> None:

    env = {**_BASE_ENV, 'BINSIM_API_KEYS': 'k1=a1,k2=a2,k3=a3'}

    config = _parse_env(env)

    assert config.api_keys == {'k1': 'a1', 'k2': 'a2', 'k3': 'a3'}


def test_strips_whitespace_in_api_keys() -> None:

    env = {**_BASE_ENV, 'BINSIM_API_KEYS': '  k1 = a1  ,  k2=a2  '}

    config = _parse_env(env)

    assert config.api_keys == {'k1': 'a1', 'k2': 'a2'}


def test_skips_empty_api_key_entries() -> None:

    env = {**_BASE_ENV, 'BINSIM_API_KEYS': 'k1=a1,,k2=a2,'}

    config = _parse_env(env)

    assert config.api_keys == {'k1': 'a1', 'k2': 'a2'}


@pytest.mark.parametrize('missing_var', ['BINSIM_DEPTH_TOKEN', 'BINSIM_STATE_DIR', 'BINSIM_API_KEYS'])
def test_missing_required_env_raises(missing_var: str) -> None:

    env = {k: v for k, v in _BASE_ENV.items() if k != missing_var}

    with pytest.raises(RuntimeError, match=f'{missing_var} is required'):
        _parse_env(env)


@pytest.mark.parametrize('empty_value', ['', '   '])
def test_empty_required_env_treated_as_missing(empty_value: str) -> None:

    env = {**_BASE_ENV, 'BINSIM_DEPTH_TOKEN': empty_value}

    with pytest.raises(RuntimeError, match='BINSIM_DEPTH_TOKEN is required'):
        _parse_env(env)


def test_api_keys_without_equals_raises() -> None:

    env = {**_BASE_ENV, 'BINSIM_API_KEYS': 'apikey-1'}

    with pytest.raises(RuntimeError, match='missing `=` separator'):
        _parse_env(env)


def test_api_keys_with_empty_account_id_raises() -> None:

    env = {**_BASE_ENV, 'BINSIM_API_KEYS': 'apikey-1='}

    with pytest.raises(RuntimeError, match='empty api_key or account_id'):
        _parse_env(env)


def test_api_keys_with_empty_api_key_raises() -> None:

    env = {**_BASE_ENV, 'BINSIM_API_KEYS': '=acc-1'}

    with pytest.raises(RuntimeError, match='empty api_key or account_id'):
        _parse_env(env)


def test_api_keys_with_duplicate_key_raises() -> None:

    env = {**_BASE_ENV, 'BINSIM_API_KEYS': 'k1=a1,k1=a2'}

    with pytest.raises(RuntimeError, match='duplicate api_key'):
        _parse_env(env)


def test_api_keys_all_empty_entries_raises() -> None:

    env = {**_BASE_ENV, 'BINSIM_API_KEYS': ',,,'}

    with pytest.raises(RuntimeError, match='BINSIM_API_KEYS'):
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
