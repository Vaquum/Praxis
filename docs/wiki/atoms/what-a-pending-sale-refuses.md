---
row: N4-07
baseline: 49aa659
created: 2026-10-23 17:30 UTC
modified: 2026-10-25 09:00 UTC
evidence:
  - claim: "A sale larger than the position less what is pending on it is refused at the intake stage"
    source: "`nexus/core/validator/intake_stage.py` 278-284"
  - claim: "Intake stands first in the order the walk is handed, the walk takes its stages in that order, and a refusal answers there and then"
    source: "`nexus/core/validator/pipeline_models.py` 50-56, handed to the walk at `praxis/launcher.py` 1010, walked in turn at `nexus/core/validator/pipeline_executor.py` 33 and 47-49, answered at 58 into 66-73"
  - claim: "Within intake, that cap is read after the simpler refusals, among them a sale asking for nothing at all"
    source: "`nexus/core/validator/intake_stage.py` 270-276"
  - claim: "A sale a host sends on the way out never reaches that walk, carrying a decision of its own that allows it"
    source: "`nexus/startup/shutdown_sequencer.py` 398-404"
  - claim: "That sale takes its size from what the strategy asked to close, with no figure subtracted from it"
    source: "`nexus/startup/shutdown_sequencer.py` 561"
---
# What a pending sale refuses

[A pending sale](what-a-pending-sale-is.md) caps what a further sale may ask for, and only on the road that asks.

## The cap

A sale larger than the position less what is pending on it is refused at the intake stage, which stands first in the order the walk takes its stages in, and a refusal is answered there and then — so no later stage weighs the sale at all. Within intake it comes after the simpler refusals, a sale asking for nothing at all being turned away before it.

That is the figure's purpose. A second sale going through the walk can ask only for what the first left.

## The road that is not capped

A sale a host sends on the way out never reaches that walk. It carries a decision of its own that allows it, and takes its size from what the strategy asked to close, with no figure subtracted from it.

So the cap holds for the sales a strategy asks for while the host is running, and not for the ones the host sends as it stops.

## Related

- [What a pending sale is](what-a-pending-sale-is.md)
- [The roads around the checks](the-roads-around-the-checks.md)

---

Created 2026-10-23 17:30 UTC · Last modified 2026-10-25 09:00 UTC
