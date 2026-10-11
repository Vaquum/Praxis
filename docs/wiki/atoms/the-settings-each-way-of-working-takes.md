---
row: P4-08
baseline: 49aa659
created: 2026-10-03 14:12 UTC
modified: 2026-10-11 11:46 UTC
evidence:
  - claim: "Seven ways of working share six kinds of settings between them"
    source: "`execution_params.py` 30-38"
  - claim: "Feeding work out at a fixed pace and buying at a fixed pace take the same kind, and no other pair does"
    source: "`execution_params.py` 30-38"
  - claim: "A command must carry the kind its way of working registers"
    source: "`praxis/core/domain/trade_command.py` 118-124"
  - claim: "The plain single order takes up to three prices, each of which may be left unset"
    source: "`single_shot_params.py` 30-32"
  - claim: "Which are needed turns on the kind of order"
    source: "`validate_trade_command.py` 221-246"
  - claim: "A price that is set must be above nought, tested by comparison alone"
    source: "`single_shot_params.py` 38-42"
  - claim: "The fixed-pace kind takes two whole numbers, used as a count of parts and a gap in seconds"
    source: "`interval_slice_params.py` 30-31, used at `execution_manager.py` 5926"
  - claim: "The count must be at least two"
    source: "`interval_slice_params.py` 37-43, the least set at 16"
  - claim: "The gap must be above nought"
    source: "`interval_slice_params.py` 45-51"
  - claim: "Both refuse true and false outright, before either bound is weighed"
    source: "`interval_slice_params.py` 38 and 46"
  - claim: "The weighted kind takes a gap in seconds, tested the same way, and a tuple of weights"
    source: "`scheduled_vwap_params.py` 35-36 and 42-48"
  - claim: "There must be at least two weights, arriving as a tuple"
    source: "`scheduled_vwap_params.py` 50-52, the least set at 20"
  - claim: "Each weight must be a finite decimal above nought"
    source: "`scheduled_vwap_params.py` 54-60"
  - claim: "Adding the weights must give exactly one, with no tolerance in the comparison"
    source: "`scheduled_vwap_params.py` 62-64, the one at 19"
  - claim: "Rounding while they are added can let a total slightly off one pass"
    source: "`scheduled_vwap_params.py` 62"
  - claim: "The count of parts for the weighted kind is taken as the count of weights"
    source: "`execution_manager.py` 467-471, the parts planned at `plan_weighted_slices.py` 58-62 and counted at `execution_manager.py` 5767"
---
# The settings each way of working takes

Every [way of working](ways-of-working-a-host-may-drive.md) carries its own settings on [a command](what-a-command-must-carry.md), which must be of the kind that way registers. There are seven ways and six kinds: feeding work out at a fixed pace and buying at a fixed pace share one, and no other pair does.

## The plain single order

Up to three prices, each of which may be left unset: the price to rest at, the price that triggers, and the price a triggered leg rests at. [Which are needed](the-prices-an-order-must-name.md) turns on the kind of order.

A price that is set must be above nought. That is a comparison alone, so an endless price passes, as does a whole number or a floating-point one; a not-a-number, and anything a decimal cannot be weighed against, break on the comparison itself.

## A fixed pace

Two whole numbers, used as a count of parts and a gap in seconds. The count must be at least two; the gap must be above nought.

Both refuse true and false outright, before either bound is weighed; what Python would otherwise make of them is Python's own affair.

## A weighted pace

A gap in seconds, tested the same way, and a tuple of weights.

There must be at least two weights, each a finite decimal above nought, and adding them must give exactly one. There is no tolerance in that comparison. Rounding while they are added is the slack: a pair whose true total sits a shade either side of one can still add to one, and pass.

No count of parts is carried here. It is taken as the count of weights.

## Related

- [Work fed out over time](work-fed-out-over-time.md)
- [What a command must carry](what-a-command-must-carry.md)
