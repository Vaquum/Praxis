'''
Split a command quantity into lot-aligned, evenly sized child slices.

Divide the total base quantity into num_slices children, each floored to
the venue lot step so every child clears the LOT_SIZE filter. The final
slice absorbs the rounding remainder so the plan sums as close to the
total as the lot grid allows, never above it. Shared by every scheme mode
that submits equal children (TWAP, Time DCA).
'''

from __future__ import annotations

from decimal import Decimal

__all__ = ['plan_even_slices']

_ZERO = Decimal(0)
_MIN_SLICES = 2


def plan_even_slices(
    total_qty: Decimal,
    num_slices: int,
    lot_step: Decimal | None,
) -> list[Decimal]:
    '''
    Compute lot-aligned, evenly sized child quantities for a scheme.

    Args:
        total_qty (Decimal): Total base quantity to execute, positive.
        num_slices (int): Number of child slices, at least 2.
        lot_step (Decimal | None): Venue LOT_SIZE step. None when the
            symbol filters are not cached, in which case each slice is an
            exact even division and the final slice takes the remainder.

    Returns:
        list[Decimal]: num_slices child quantities. The first num_slices-1
            entries are equal; the last carries the remainder. The sum is
            at or below total_qty, short by less than one lot step.

    Raises:
        ValueError: If total_qty is not positive, num_slices is below 2,
            or the lot grid cannot fit one positive quantity per slice.
    '''

    if not isinstance(total_qty, Decimal) or not total_qty.is_finite() or total_qty <= _ZERO:
        msg = f'total_qty must be a positive, finite Decimal, got {total_qty}'
        raise ValueError(msg)

    if num_slices < _MIN_SLICES:
        msg = f'num_slices must be at least {_MIN_SLICES}, got {num_slices}'
        raise ValueError(msg)

    if lot_step is None:
        base = total_qty / num_slices
        last = total_qty - base * (num_slices - 1)

        return [base] * (num_slices - 1) + [last]

    base = (total_qty / num_slices // lot_step) * lot_step

    if base <= _ZERO:
        msg = (
            f'lot step {lot_step} too coarse to split {total_qty} '
            f'into {num_slices} positive slices'
        )
        raise ValueError(msg)

    last = ((total_qty - base * (num_slices - 1)) // lot_step) * lot_step

    if last <= _ZERO:
        msg = (
            f'lot step {lot_step} leaves no quantity for the final slice '
            f'of {total_qty} across {num_slices} slices'
        )
        raise ValueError(msg)

    return [base] * (num_slices - 1) + [last]
