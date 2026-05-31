'''Tests for `_positive_float_env` env-var parser.

Pins: unset / empty returns default; valid positive numbers are parsed;
non-numeric values raise `RuntimeError` with env-var name + value + expected
shape; zero / negative values raise `RuntimeError`; the operator-visible
error message survives the per-account thread's BLE001 catch.
'''

from __future__ import annotations

import pytest

from praxis.launcher import _positive_float_env


def test_unset_env_returns_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv('NEXUS_TEST_INTERVAL_SECONDS', raising=False)
    assert _positive_float_env('NEXUS_TEST_INTERVAL_SECONDS', 42.0) == 42.0


def test_empty_env_returns_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv('NEXUS_TEST_INTERVAL_SECONDS', '')
    assert _positive_float_env('NEXUS_TEST_INTERVAL_SECONDS', 42.0) == 42.0


def test_valid_numeric_env_parsed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv('NEXUS_TEST_INTERVAL_SECONDS', '600')
    assert _positive_float_env('NEXUS_TEST_INTERVAL_SECONDS', 300.0) == 600.0


def test_valid_float_env_parsed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv('NEXUS_TEST_INTERVAL_SECONDS', '2.5')
    assert _positive_float_env('NEXUS_TEST_INTERVAL_SECONDS', 30.0) == 2.5


def test_non_numeric_env_raises_with_actionable_message(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv('NEXUS_TEST_INTERVAL_SECONDS', '30s')

    with pytest.raises(RuntimeError) as excinfo:
        _positive_float_env('NEXUS_TEST_INTERVAL_SECONDS', 30.0)

    msg = str(excinfo.value)
    assert 'NEXUS_TEST_INTERVAL_SECONDS' in msg
    assert "'30s'" in msg
    assert 'positive float' in msg


def test_zero_env_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv('NEXUS_TEST_INTERVAL_SECONDS', '0')

    with pytest.raises(RuntimeError, match=r'NEXUS_TEST_INTERVAL_SECONDS'):
        _positive_float_env('NEXUS_TEST_INTERVAL_SECONDS', 30.0)


def test_negative_env_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv('NEXUS_TEST_INTERVAL_SECONDS', '-5')

    with pytest.raises(RuntimeError, match=r'must be a positive, finite number'):
        _positive_float_env('NEXUS_TEST_INTERVAL_SECONDS', 30.0)


def test_inf_env_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    '''Pin: `float("inf") <= 0` is False; without an explicit
    finiteness guard, the value propagates to `threading.Timer` and
    silently disables the scheduler (timer never fires).
    '''

    monkeypatch.setenv('NEXUS_TEST_INTERVAL_SECONDS', 'inf')

    with pytest.raises(RuntimeError, match=r'must be a positive, finite number'):
        _positive_float_env('NEXUS_TEST_INTERVAL_SECONDS', 30.0)


def test_nan_env_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    '''Pin: `float("nan") <= 0` is False; without an explicit
    finiteness guard, the NaN propagates to `threading.Timer` with
    undefined behaviour.
    '''

    monkeypatch.setenv('NEXUS_TEST_INTERVAL_SECONDS', 'nan')

    with pytest.raises(RuntimeError, match=r'must be a positive, finite number'):
        _positive_float_env('NEXUS_TEST_INTERVAL_SECONDS', 30.0)
