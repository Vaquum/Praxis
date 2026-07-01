'''Percentile primitives matching Limen's backtest metric convention.

Limen reports each distribution metric as a p5/p50/p95 triple computed with
NumPy's linear-interpolation quantile over the finite values only. These
helpers reproduce that exactly so replay and paper-trading metrics are
directly comparable to Limen's.
'''

from __future__ import annotations

from collections.abc import Iterable

import numpy as np

__all__ = ['finite_values', 'quantile_triple']

_QUANTILES = (0.05, 0.50, 0.95)
_DEFAULT_DECIMALS = 1


def finite_values(values: Iterable[float | None]) -> np.ndarray:

    '''Return the finite values as a float array, dropping NaN and Inf.

    Args:
        values: An iterable of floats or `None`; `None`, NaN, and Inf are
            dropped. Entries must already be numeric or `None` — a
            non-numeric value raises `ValueError` when coerced to float.

    Returns:
        A 1-D float array of only the finite values, in input order.
    '''

    arr = np.asarray(list(values), dtype=float)

    return np.asarray(arr[np.isfinite(arr)])


def quantile_triple(
    values: Iterable[float | None],
    decimals: int = _DEFAULT_DECIMALS,
) -> tuple[float | None, float | None, float | None]:

    '''Return the (p5, p50, p95) quantiles of the finite values.

    Uses NumPy's default linear interpolation. Each quantile is rounded to
    `decimals`. Returns `(None, None, None)` when no finite values exist.

    Args:
        values: Any iterable of numbers.
        decimals: Decimal places to round each quantile to.

    Returns:
        The p5, p50, and p95 quantiles, or `(None, None, None)` if empty.
    '''

    arr = finite_values(values)

    if arr.size == 0:
        return (None, None, None)

    p5, p50, p95 = (
        round(float(np.quantile(arr, q, method='linear')), decimals) for q in _QUANTILES
    )

    return (p5, p50, p95)
