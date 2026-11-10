---
row: N5-04
baseline: 49aa659
created: 2026-10-25 11:30 UTC
modified: 2026-10-26 07:47 UTC
evidence:
  - claim: "A host shutting down asks each strategy in turn what it wants done and keeps whatever it answers with"
    source: "`nexus/startup/shutdown_sequencer.py` 305-306 into 325-328"
  - claim: "Of what it kept, the sales are sent down this road and the aborts down another, the rest being dropped before either"
    source: "`nexus/startup/shutdown_sequencer.py` 382-386, the dropping at 343-363"
  - claim: "A record is built for each sale and sent, carrying the position's symbol, the side that closes it, and the size the strategy asked to close"
    source: "`nexus/startup/shutdown_sequencer.py` 394-407, the side worked out at 552-554, the rest at 555-565 into `nexus/infrastructure/praxis_connector/translate.py` 107-124"
  - claim: "A sale whose record cannot be built is answered with nothing and never sent"
    source: "`nexus/startup/shutdown_sequencer.py` 394-396"
  - claim: "The record carries a decision allowing the sale, where a sale a strategy submits in the ordinary way asks the walk for one"
    source: "`nexus/startup/shutdown_sequencer.py` 401 against `nexus/strategy/action_submit.py` 242"
  - claim: "Its command identifier is made on the spot from the strategy's name and a fresh random tail"
    source: "`nexus/startup/shutdown_sequencer.py` 555"
  - claim: "The amount and the fee guessed for it are both left at nought"
    source: "`nexus/startup/shutdown_sequencer.py` 564-565"
  - claim: "A send that raises is logged and answered with nothing, and the loop over what was kept goes on to the next"
    source: "`nexus/startup/shutdown_sequencer.py` 407-414 under the loop at 382-384"
  - claim: "The record of the sale against the position is built after the command has been handed over, and a position gone from the book by then, or an amount at or below nought, ends that building"
    source: "`nexus/startup/shutdown_sequencer.py` 407 before 425-431, the ending at 432-443 raised at 499-516"
  - claim: "That ending answers before the pending figure is touched, so the figure stands as it was"
    source: "`nexus/startup/shutdown_sequencer.py` 443 before 458"
---
# The sale a host sends as it stops

A shutdown sale is one a strategy asks for as the host goes down, carrying a decision that allows it.

## Which positions get one

The host asks each strategy in turn what it wants done and keeps whatever it answers with. Of that, the sales go down this road and the aborts down another; the rest are dropped before either. A position a strategy says nothing about gets no sale: the host sends what it is told to.

## What the sale carries

A record is built for each and sent: the position's symbol, the side worked out to close it, and the size the strategy asked to close. One whose record cannot be built is answered with nothing and never sent. The command identifier is made on the spot from the strategy's name and a fresh random tail. The amount and the fee guessed for it are both left at nought.

## What it skips

It carries a decision allowing the sale rather than asking [the walk](the-checks-a-decision-passes.md) for one, so [what weighs it and what does not](what-weighs-a-shutdown-sale.md) differs from an ordinary sale.

## What can go wrong behind it

A send that raises is logged and answered with nothing, and the loop goes on to the next thing the host kept.

The record of the sale against the position is built after the command has been handed over to be sent. A position gone from the book by then, or an amount at or below nought, ends that building — and [the pending figure](what-a-pending-sale-is.md) is left as it was, with the command already on its way.

## Related

- [What a pending sale is](what-a-pending-sale-is.md)
- [The roads around the checks](the-roads-around-the-checks.md)

---

Created 2026-10-25 11:30 UTC · Last modified 2026-10-26 07:47 UTC
