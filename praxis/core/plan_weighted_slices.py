'''
Split a command quantity into lot-aligned child slices by volume weight.

Divide the total base quantity across a strategy-supplied volume-weight
curve, one child per weight, each floored to the venue lot step so every
child clears the LOT_SIZE filter. The final slice absorbs the rounding
remainder so the plan sums as close to the total as the lot grid allows,
never above it. Used by Scheduled VWAP, whose weights are supplied by the
decision layer; Praxis does not source live volume.
'''

from __future__ import annotations

from decimal import Decimal

__all__ = ['plan_weighted_slices']

_ZERO = Decimal(0)
_MIN_SLICES = 2


def plan_weighted_slices(
    total_qty: Decimal,
    volume_weights: tuple[Decimal, ...],
    lot_step: Decimal | None,
) -> list[Decimal]:
    '''
    Compute lot-aligned child quantities weighted by a volume curve.

    Args:
        total_qty (Decimal): Total base quantity to execute, positive.
        volume_weights (tuple[Decimal, ...]): Per-slice weights, at least 2,
            each positive, summing to 1.
        lot_step (Decimal | None): Venue LOT_SIZE step. None when the
            symbol filters are not cached, in which case each slice is an
            exact weighted division and the final slice takes the remainder.

    Returns:
        list[Decimal]: One child quantity per weight. The first n-1 entries
            are each weight * total_qty (lot-floored when a step is given);
            the last carries the remainder. The sum is at or below
            total_qty, short by less than one lot step per slice.

    Raises:
        ValueError: If total_qty is not positive, fewer than two weights are
            given, or the lot grid cannot fit one positive quantity per
            slice.
    '''

    if not isinstance(total_qty, Decimal) or not total_qty.is_finite() or total_qty <= _ZERO:
        msg = f'total_qty must be a positive, finite Decimal, got {total_qty}'
        raise ValueError(msg)

    if len(volume_weights) < _MIN_SLICES:
        msg = f'volume_weights must have at least {_MIN_SLICES} entries'
        raise ValueError(msg)

    if lot_step is None:
        head = [weight * total_qty for weight in volume_weights[:-1]]
        last = total_qty - sum(head, _ZERO)

        return [*head, last]

    head = []
    for weight in volume_weights[:-1]:
        slice_qty = (weight * total_qty // lot_step) * lot_step
        if slice_qty <= _ZERO:
            msg = (
                f'lot step {lot_step} too coarse for weight {weight} '
                f'of {total_qty}'
            )
            raise ValueError(msg)

        head.append(slice_qty)

    last = ((total_qty - sum(head, _ZERO)) // lot_step) * lot_step

    if last <= _ZERO:
        msg = (
            f'lot step {lot_step} leaves no quantity for the final slice '
            f'of {total_qty} across {len(volume_weights)} weighted slices'
        )
        raise ValueError(msg)

    return [*head, last]
