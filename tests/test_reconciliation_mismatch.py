'''Tests for the ReconciliationMismatch domain event (WP-Praxis-0009).'''

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest

from praxis.core.domain.events import ReconciliationMismatch

_TS = datetime(2099, 1, 1, tzinfo=UTC)
_ACCT = 'acc-1'


def _mismatch(**overrides: object) -> ReconciliationMismatch:
    kwargs: dict[str, object] = {
        'account_id': _ACCT,
        'timestamp': _TS,
        'reconciliation_mismatch_id': 'recon-1',
        'asset': 'USDT',
        'expected': Decimal('1000'),
        'actual': Decimal('995.5'),
    }
    kwargs.update(overrides)
    return ReconciliationMismatch(**kwargs)  # type: ignore[arg-type]


class TestReconciliationMismatch:

    def test_valid_mismatch_constructs(self) -> None:
        assert _mismatch().asset == 'USDT'

    def test_delta_is_actual_minus_expected(self) -> None:
        mismatch = _mismatch(expected=Decimal('1000'), actual=Decimal('995.5'))

        assert mismatch.delta == Decimal('-4.5')

    def test_empty_asset_rejected(self) -> None:
        with pytest.raises(ValueError, match='asset'):
            _mismatch(asset='')

    def test_empty_id_rejected(self) -> None:
        with pytest.raises(ValueError, match='reconciliation_mismatch_id'):
            _mismatch(reconciliation_mismatch_id='')

    def test_non_finite_expected_rejected(self) -> None:
        with pytest.raises(ValueError, match='expected must be a finite Decimal'):
            _mismatch(expected=Decimal('NaN'))

    def test_non_finite_actual_rejected(self) -> None:
        with pytest.raises(ValueError, match='actual must be a finite Decimal'):
            _mismatch(actual=Decimal('Infinity'))

    def test_zero_delta_rejected(self) -> None:
        with pytest.raises(ValueError, match='expected != actual'):
            _mismatch(expected=Decimal('1000'), actual=Decimal('1000'))

    def test_naive_timestamp_rejected(self) -> None:
        with pytest.raises(ValueError, match='timezone-aware'):
            _mismatch(timestamp=datetime(2099, 1, 1))
