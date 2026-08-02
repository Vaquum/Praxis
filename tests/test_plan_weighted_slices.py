'''
Tests for plan_weighted_slices volume-weighted child splitting.
'''

from __future__ import annotations

from decimal import Decimal

import pytest

from praxis.core.plan_weighted_slices import plan_weighted_slices


def test_weighted_split_without_lot_step() -> None:
    plan = plan_weighted_slices(
        Decimal('1'),
        (Decimal('0.5'), Decimal('0.3'), Decimal('0.2')),
        None,
    )

    assert plan == [Decimal('0.5'), Decimal('0.3'), Decimal('0.2')]
    assert sum(plan) == Decimal('1')


def test_remainder_falls_to_last_slice_without_lot_step() -> None:
    plan = plan_weighted_slices(
        Decimal('3'),
        (Decimal('0.3333'), Decimal('0.3333'), Decimal('0.3334')),
        None,
    )

    assert plan[0] == Decimal('0.3333') * Decimal('3')
    assert sum(plan) == Decimal('3')


def test_lot_aligned_weighted_split_floors_each_slice() -> None:
    plan = plan_weighted_slices(
        Decimal('1'),
        (Decimal('0.5'), Decimal('0.3'), Decimal('0.2')),
        Decimal('0.001'),
    )

    assert plan[0] == Decimal('0.5')
    assert plan[1] == Decimal('0.3')
    assert all(q % Decimal('0.001') == 0 for q in plan)
    assert sum(plan) <= Decimal('1')


def test_lot_aligned_weighted_split_drops_dust_into_last() -> None:
    plan = plan_weighted_slices(
        Decimal('1'),
        (Decimal('0.333'), Decimal('0.333'), Decimal('0.334')),
        Decimal('0.01'),
    )

    assert all(q % Decimal('0.01') == 0 for q in plan)
    assert Decimal('1') - sum(plan) < Decimal('0.01')


def test_rejects_non_positive_total() -> None:
    with pytest.raises(ValueError, match='total_qty'):
        plan_weighted_slices(Decimal('0'), (Decimal('0.5'), Decimal('0.5')), None)


def test_rejects_fewer_than_two_weights() -> None:
    with pytest.raises(ValueError, match='at least 2'):
        plan_weighted_slices(Decimal('1'), (Decimal('1'),), None)


def test_rejects_lot_step_too_coarse_for_a_weight() -> None:
    with pytest.raises(ValueError, match='too coarse'):
        plan_weighted_slices(
            Decimal('0.02'),
            (Decimal('0.1'), Decimal('0.9')),
            Decimal('1'),
        )
