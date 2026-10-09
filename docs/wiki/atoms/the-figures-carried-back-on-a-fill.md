---
row: P4-29
baseline: 49aa659
created: 2026-10-02 09:55 UTC
modified: 2026-10-04 11:43 UTC
evidence:
  - claim: "The amount and the money are differences against what crossed last time"
    source: "`outcome_translator.py` 191-192, the running marks set at 208-209"
  - claim: "The money is Praxis's own running total over the fills admitted to the command"
    source: "`outcome_translator.py` 190, totalled at `execution_manager.py` 2505-2534 and 2561-2562, read at 2588-2591 and carried in at 4339-4341"
  - claim: "The price is the money divided by the amount"
    source: "`outcome_translator.py` 281 and 311"
  - claim: "The fee is a rate applied to that money"
    source: "`outcome_translator.py` 282 and 312"
  - claim: "The rate must be a finite decimal, and at least nought"
    source: "`outcome_translator.py` 118-124"
  - claim: "A part-fill and an ending report what remains as the target less the amount filled"
    source: "`outcome_translator.py` 283-287 and 348-352"
  - claim: "Where no target amount was named, that figure is left absent"
    source: "`outcome_translator.py` 285-287, reachable where a command is sized in money at `praxis/core/domain/trade_command.py` 86-104 into `execution_manager.py` 10789"
  - claim: "A full fill leaves it absent whatever the target"
    source: "`outcome_translator.py` 314-325"
  - claim: "A part-fill and a full fill pass on whichever of two slippage measures is there"
    source: "`outcome_translator.py` 299-300 and 323-324"
  - claim: "Both start absent and are each worked out only where their own price is to hand"
    source: "`execution_manager.py` 4360-4368 and 4378-4383"
  - claim: "A measure compares the command's running average price against that price, which is also what it is divided by"
    source: "`execution_manager.py` 4363-4368 and 4378-4383, the figures taken at 4339-4341 and divided at 4356-4358"
  - claim: "An outcome raised from the venue's feed is built without either"
    source: "`execution_manager.py` 10733-10741"
  - claim: "An acknowledgement, a refusal and an ending carry neither either"
    source: "`outcome_translator.py` 265-270, 331-337 and 354-361"
---
# The figures carried back on a fill

Praxis keeps running totals for a command. Nexus wants one event at a time, so [an outcome crossing back](how-an-outcome-crosses-back.md) on a [fill](what-a-fill-is.md) carries differences rather than totals.

## The differences

The amount is what has been filled now, less what had been filled when an outcome last crossed. The money is the same subtraction over the money — Praxis's own running total across the fills admitted to the command.

The price for the event is then the money divided by the amount, and the fee a rate applied to that money. The rate must be a finite decimal and at least nought.

## What remains

A part-fill and an ending report what remains as the target less the amount filled. Where a command was sized in money and named no target amount, that figure is left absent.

A full fill leaves it absent whatever the target, since nothing remains once a command is filled.

## Two measures that do not match the event

A part-fill and a full fill pass on whichever of two slippage measures is there. Both start absent, and each is worked out only where the price it needs is to hand — the midpoint of [the book](the-order-book.md) when the order went out, or the price the decision was made against. An outcome raised from [the venue's feed](the-venue-feed.md) carries neither, and neither do an acknowledgement, a refusal and an ending.

Where a measure is there, it does not describe the event it rides on. It compares the command's running average price against the one price it is measured from, which is also what the difference is divided by — so it covers every fill admitted so far, rather than this one.

## Related

- [How an outcome crosses back](how-an-outcome-crosses-back.md)
- [The figures an outcome reports](the-figures-an-outcome-reports.md)
