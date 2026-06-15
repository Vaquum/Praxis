'''Tests for `_resolve_mark_price_series` (Conduit price cutover).

The launcher prices ENTER fallback and mark-to-market against a single
`(series, interval_seconds)` pair read from the manifest's per-strategy
`signal` blocks. This module pins the resolution rules: single-series
default, `PRAXIS_MARK_PRICE_SERIES` override, multi-series ambiguity,
and the missing-interval error for an unknown override series.
'''

from __future__ import annotations

from dataclasses import dataclass

import pytest

from praxis.launcher import _resolve_mark_price_series


@dataclass(frozen=True)
class _FakeSignal:
    series: str
    interval_seconds: int


@dataclass(frozen=True)
class _FakeSpec:
    signal: _FakeSignal


@dataclass(frozen=True)
class _FakeManifest:
    strategies: tuple[_FakeSpec, ...]


def _manifest(*pairs: tuple[str, int]) -> _FakeManifest:
    return _FakeManifest(
        strategies=tuple(
            _FakeSpec(signal=_FakeSignal(series=series, interval_seconds=interval))
            for series, interval in pairs
        ),
    )


def test_single_series_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv('PRAXIS_MARK_PRICE_SERIES', raising=False)

    series, interval = _resolve_mark_price_series(
        _manifest(('time_15m', 900)),  # type: ignore[arg-type]
    )

    assert series == 'time_15m'
    assert interval == 900


def test_env_series_override_matching_manifest(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv('PRAXIS_MARK_PRICE_SERIES', 'time_1m')

    series, interval = _resolve_mark_price_series(
        _manifest(('time_15m', 900), ('time_1m', 60)),  # type: ignore[arg-type]
    )

    assert series == 'time_1m'
    assert interval == 60


def test_env_series_override_unknown_with_interval(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv('PRAXIS_MARK_PRICE_SERIES', 'time_5m')
    monkeypatch.setenv('PRAXIS_MARK_PRICE_INTERVAL_SECONDS', '300')

    series, interval = _resolve_mark_price_series(
        _manifest(('time_15m', 900)),  # type: ignore[arg-type]
    )

    assert series == 'time_5m'
    assert interval == 300


def test_multiple_series_unset_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv('PRAXIS_MARK_PRICE_SERIES', raising=False)

    with pytest.raises(RuntimeError, match='multiple signal series'):
        _resolve_mark_price_series(
            _manifest(('time_15m', 900), ('time_1m', 60)),  # type: ignore[arg-type]
        )


def test_unknown_series_missing_interval_raises(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv('PRAXIS_MARK_PRICE_SERIES', 'time_5m')
    monkeypatch.delenv('PRAXIS_MARK_PRICE_INTERVAL_SECONDS', raising=False)

    with pytest.raises(RuntimeError, match='PRAXIS_MARK_PRICE_INTERVAL_SECONDS'):
        _resolve_mark_price_series(
            _manifest(('time_15m', 900)),  # type: ignore[arg-type]
        )


def test_same_series_conflicting_intervals_raises(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv('PRAXIS_MARK_PRICE_SERIES', raising=False)

    with pytest.raises(RuntimeError, match='conflicting interval_seconds'):
        _resolve_mark_price_series(
            _manifest(('time_15m', 900), ('time_15m', 300)),  # type: ignore[arg-type]
        )
