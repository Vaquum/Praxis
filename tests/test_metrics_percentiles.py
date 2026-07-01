import numpy as np

from praxis.metrics.percentiles import finite_values, quantile_triple


def test_finite_values_drops_nan_and_inf():
    arr = finite_values([1.0, float('nan'), 2.0, float('inf'), -float('inf'), 3.0])

    assert list(arr) == [1.0, 2.0, 3.0]


def test_finite_values_empty():
    assert finite_values([]).size == 0
    assert finite_values([float('nan'), float('inf')]).size == 0


def test_quantile_triple_matches_numpy_linear():
    values = [10.0, 20.0, 30.0, 40.0, 50.0, 60.0, 70.0, 80.0, 90.0, 100.0]
    p5, p50, p95 = quantile_triple(values, decimals=1)

    assert p5 == round(float(np.quantile(values, 0.05)), 1)
    assert p50 == round(float(np.quantile(values, 0.50)), 1)
    assert p95 == round(float(np.quantile(values, 0.95)), 1)


def test_quantile_triple_rounds_to_decimals():
    p5, p50, _p95 = quantile_triple([1.0, 2.0, 3.0], decimals=3)

    assert p50 == 2.0
    assert isinstance(p5, float)


def test_quantile_triple_empty_returns_none():
    assert quantile_triple([]) == (None, None, None)
    assert quantile_triple([float('nan'), float('inf')]) == (None, None, None)


def test_quantile_triple_ignores_non_finite_in_mix():
    clean = quantile_triple([1.0, 2.0, 3.0, 4.0, 5.0])
    mixed = quantile_triple([1.0, 2.0, float('nan'), 3.0, 4.0, float('inf'), 5.0])

    assert clean == mixed


def test_single_value():
    assert quantile_triple([42.0]) == (42.0, 42.0, 42.0)
