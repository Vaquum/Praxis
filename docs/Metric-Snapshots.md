# Metric Snapshots

Praxis has portfolio-basis and Limen bar-basis metric engines. They compute return distributions independently and pass them to `praxis.metrics.snapshot_result.build_snapshot_result` for one shared output schema, unit conversion, and rounding policy. This helper assembles already-computed distributions; it does not derive positions or trades from raw venue data.

## `build_snapshot_result`

Compute the published snapshot metric triples from return distributions.

NOTE: All arguments are keyword-only to distinguish same-shaped series.

### Args

- `edge_per_signal_bps (Sequence[float])`: Per-in-position-step gross return in bps
- `trade_net (Sequence[float])`: Per-trade net return as a fraction, scaled to bps here
- `trade_gross (Sequence[float])`: Per-trade gross return as a fraction, paired with `trade_net` to compute cost drag
- `rolling_return_net_bps (Sequence[float])`: Per-window net return in bps, also the CVaR population
- `return_on_exposure (Sequence[float | None])`: Per-window net return in bps divided by the in-position fraction, or `None` without exposure
- `drawdown_depth_bps (Sequence[float])`: Per-episode trough depth in bps
- `drawdown_duration_days (Sequence[float])`: Per-episode duration in days

### Returns

`dict[str, float | None]`: `edge_per_signal_bps`, `trade_pnl_net_bps`, `cost_drag_bps`, `rolling_return_net_bps`, `return_on_exposure`, `drawdown_depth_bps`, and `drawdown_duration_days` each suffixed with `_p5`, `_p50`, and `_p95`, plus scalar `cvar_95_return_bps`, with `None` for missing values

### Edge Cases And Conventions

`trade_net` and `trade_gross` must have matching lengths; mismatches raise `ValueError`. Trade returns are multiplied by 10,000 to obtain basis points. Cost drag is gross minus net, also in basis points. Non-finite observations are excluded from percentile and CVaR populations; a distribution with no finite observations produces `None` values. Percentiles use linear interpolation, with one decimal place for basis-point metrics and three for drawdown duration in days. CVaR is the mean of finite window returns at or below their linear-interpolation fifth percentile, rounded to one decimal place.

The engines preserve their own trade, window, and drawdown calculations. Sharing the result assembler does not imply that the two bases produce identical return distributions.

## Read Next

- [Trade Outcomes](Trade-Outcomes.md)
- [Execution Manager](Execution-Manager.md)
