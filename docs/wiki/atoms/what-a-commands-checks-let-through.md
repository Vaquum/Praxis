---
row: P4-33
baseline: 49aa659
created: 2026-10-03 13:13 UTC
modified: 2026-10-04 11:43 UTC
evidence:
  - claim: "The test on the four names rejects whatever counts as nothing, which takes in an empty string, a missing value, nought and false"
    source: "`_require_str.py` 28-30"
  - claim: "Anything else of any kind passes it, and the wider check adds no test of kind"
    source: "`_require_str.py` 28-30, with nothing further in `validate_trade_command.py`"
  - claim: "The written-down acceptance uses the same test"
    source: "`events.py` 140-144"
  - claim: "A trade name that cannot be used as a key is caught only when the books are updated, after the command is written down and queued"
    source: "`trading_state.py` 392-396, reached past `execution_manager.py` 3525, 3550 and 3565-3573"
  - claim: "One that can be used as a key is not caught there at all, and nor is any of them where no strategy is named"
    source: "`trading_state.py` 392-396"
  - claim: "A command's own name of the wrong kind is caught earlier, by the taking out of hyphens"
    source: "`generate_client_order_id.py` 105-110"
  - claim: "The deadline is tested by comparison alone, so a floating-point not-a-number passes, and so does a floating-point endless value"
    source: "`praxis/core/domain/trade_command.py` 106-108"
  - claim: "Both are refused later, where the deadline is turned into a moment"
    source: "`execution_manager.py` 2925"
  - claim: "A string, a list, nothing at all, or a decimal not-a-number refuses on the comparison; a decimal above nought gets past it"
    source: "`praxis/core/domain/trade_command.py` 106-108"
  - claim: "Work fed out in slices reaches that step before it sends anything"
    source: "`execution_manager.py` 3995 reaching 2925"
  - claim: "A ladder does too"
    source: "`execution_manager.py` 4004 reaching 2925"
  - claim: "A plain single order reaches it only where it is left waiting or part-filled, so one filled at once never meets it"
    source: "`execution_manager.py` 4411-4414 reaching 2925"
  - claim: "A reference price is tested by comparison alone, so an endless one passes"
    source: "`praxis/core/domain/trade_command.py` 110-112"
  - claim: "An endless size is refused, being tested for finiteness as well"
    source: "`praxis/core/domain/trade_command.py` 90-104"
  - claim: "A decimal endless price later divides into itself, which refuses"
    source: "`execution_manager.py` 4378-4383"
  - claim: "A floating-point endless price refuses one step earlier, at the subtraction"
    source: "`execution_manager.py` 4380"
---
# What a command's checks let through

[A command's checks](what-a-command-must-carry.md) are comparisons. Each rejects on one ground, and a value wrong on some other ground gets past.

## The four names

The test on them rejects whatever counts as nothing — an empty string, a missing value, nought, false. Anything else of any kind passes, and the wider check adds no test of kind. The acceptance written down uses the same test again.

So a [trade name](what-a-trade-is.md) that is a number or a list is written down, queued and installed. A list is caught when the books are updated, only because a list cannot be used as a key; a number is caught nowhere. Where no strategy is named, that step is skipped.

A command's own name is caught earlier, by the attempt to take its hyphens out.

## The deadline

The deadline is tested by comparison with nought alone. A floating-point not-a-number compares as neither above nor below, so it passes, and so does a floating-point endless value. A string, a list, nothing at all, or a decimal not-a-number refuses on the comparison.

A decimal above nought gets past it too, the check being about sign alone.

What passes is caught where the deadline becomes a moment. Work fed out in slices, and a ladder, reach that step before sending anything. A plain single order reaches it only where it is left waiting or part-filled — one filled at once never meets it.

## The reference price

The reference price is tested the same way, so an endless price passes where an endless size would not — the sizes being tested for finiteness as well.

A decimal endless price reaching the measurement of slippage divides into itself, which refuses. A floating-point one refuses a step earlier, at the subtraction.

## Related

- [What a command must carry](what-a-command-must-carry.md)
- [What turns work away](what-turns-work-away.md)
