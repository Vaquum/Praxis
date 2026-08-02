'''
Tests for plan_even_slices lot-aligned child splitting.
'''

from __future__ import annotations

from decimal import Decimal

import pytest

from praxis.core.plan_even_slices import plan_even_slices


def test_even_split_without_lot_step() -> None:
    plan = plan_even_slices(Decimal('1'), 4, None)

    assert plan == [Decimal('0.25'), Decimal('0.25'), Decimal('0.25'), Decimal('0.25')]
    assert sum(plan) == Decimal('1')


def test_remainder_falls_to_last_slice_without_lot_step() -> None:
    plan = plan_even_slices(Decimal('1'), 3, None)

    assert plan[0] == plan[1]
    assert sum(plan) == Decimal('1')
    assert plan[2] == Decimal('1') - plan[0] * 2


def test_lot_aligned_split_floors_each_slice() -> None:
    plan = plan_even_slices(Decimal('1'), 3, Decimal('0.001'))

    assert plan[0] == Decimal('0.333')
    assert plan[1] == Decimal('0.333')
    assert plan[2] == Decimal('0.334')
    assert sum(plan) == Decimal('1')


def test_lot_aligned_split_drops_dust_into_shortfall() -> None:
    plan = plan_even_slices(Decimal('1'), 3, Decimal('0.01'))

    assert plan[0] == Decimal('0.33')
    assert plan[2] == Decimal('0.34')
    assert all(q % Decimal('0.01') == 0 for q in plan)
    assert Decimal('1') - sum(plan) < Decimal('0.01')


def test_every_slice_is_a_lot_step_multiple() -> None:
    plan = plan_even_slices(Decimal('0.5'), 4, Decimal('0.00001'))

    assert all(q % Decimal('0.00001') == 0 for q in plan)
    assert sum(plan) <= Decimal('0.5')


def test_rejects_non_positive_total() -> None:
    with pytest.raises(ValueError, match='total_qty'):
        plan_even_slices(Decimal('0'), 3, Decimal('0.001'))


def test_rejects_num_slices_below_two() -> None:
    with pytest.raises(ValueError, match='num_slices'):
        plan_even_slices(Decimal('1'), 1, Decimal('0.001'))


def test_rejects_lot_step_too_coarse() -> None:
    with pytest.raises(ValueError, match='too coarse'):
        plan_even_slices(Decimal('0.001'), 3, Decimal('1'))
