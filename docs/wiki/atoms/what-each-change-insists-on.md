---
row: P4-35
baseline: 49aa659
created: 2026-10-03 16:40 UTC
modified: 2026-10-04 11:43 UTC
evidence:
  - claim: "A single order's change offers three prices, any of them alone"
    source: "`single_shot_modify.py` 31-33 and 39-43"
  - claim: "A part-shown order's change offers the shown amount and the resting price"
    source: "`iceberg_modify.py` 29-30 and 36-40"
  - claim: "A protective pair's change offers five fields"
    source: "`bracket_modify.py` 37-41"
  - claim: "Each of its two legs takes a price or an offset, and giving both is refused"
    source: "`bracket_modify.py` 59-65"
  - claim: "An offset is read in hundredths of a percent"
    source: "`execution_manager.py` 9872-9889, the divisor at 146"
  - claim: "A fixed-pace change offers a count of parts and a gap, the count at least two and the gap above nought"
    source: "`interval_slice_modify.py` 42-56"
  - claim: "The gap is read as seconds"
    source: "`execution_manager.py` 10154"
  - claim: "The count excludes true and false"
    source: "`interval_slice_modify.py` 43"
  - claim: "So does the gap"
    source: "`interval_slice_modify.py` 51"
  - claim: "A weighted change offers weights and a gap, the weights held as the settings hold them"
    source: "`scheduled_vwap_modify.py` 47-62 against `scheduled_vwap_params.py` 50-64"
  - claim: "A ladder's change offers price levels and weights"
    source: "`ladder_dca_modify.py` 36-37 and 43-45"
  - claim: "Its levels must be a tuple of at least two finite decimals above nought"
    source: "`ladder_dca_modify.py` 48-55"
  - claim: "They must run one way throughout, every step rising or every step falling"
    source: "`ladder_dca_modify.py` 57-62"
  - claim: "Its weights must be at least two, each a finite decimal above nought, adding to one"
    source: "`ladder_dca_modify.py` 65-76"
  - claim: "Where both are given, they must be the same length"
    source: "`ladder_dca_modify.py` 78-84"
---
# What each change insists on

Each of the six [kinds of change](the-change-each-way-of-working-accepts.md) names its own fields and its own rules.

## One price at a time

A single order's change offers three prices — the resting price, the trigger, and the triggered leg's price — any one of them alone. A [part-shown order's](part-shown-orders.md) change offers two: the amount shown and the price it rests at.

## A pair of legs

[A protective pair's](protection.md) change offers five fields. Each of its two legs takes either an outright price or an offset in hundredths of a percent, and giving both for one leg is refused. The fifth field is the price the stop leg rests at once triggered.

## A pace

A [fixed-pace](work-fed-out-over-time.md) change offers a count of parts and a gap in seconds — the count at least two, the gap above nought, both excluding true and false.

A weighted change offers weights and a gap instead. Its weights are held exactly as the settings hold them: a tuple of at least two finite decimals above nought, adding to one.

## A ladder

[A ladder's](orders-at-several-prices.md) change offers price levels and weights.

The levels must be a tuple of at least two finite decimals above nought, and must run one way throughout — every step rising, or every step falling. A level repeated breaks that, since a repeat is neither.

The weights are held as the weighted kind's are. Where both levels and weights are given, they must be the same length.

## Related

- [The change each way of working accepts](the-change-each-way-of-working-accepts.md)
- [Changing work already sent](changing-work-already-sent.md)
