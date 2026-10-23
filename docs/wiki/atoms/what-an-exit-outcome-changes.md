---
row: N2-01
baseline: 49aa659
created: 2026-10-18 19:00 UTC
modified: 2026-10-23 09:00 UTC
evidence:
  - claim: "An exit fill takes its size off the position, and takes the same off what the position has pending, or all of it where less is pending than the fill filled"
    source: "`nexus/infrastructure/praxis_connector/outcome_processor.py` 558-560"
  - claim: "A position whose size reaches nought is dropped from the record"
    source: "`nexus/infrastructure/praxis_connector/outcome_processor.py` 594-595, nought read at `nexus/core/domain/position.py` 91-94"
  - claim: "A fill finishing the order, meant to close the whole position and leaving some of it, loses the rest as well, the remainder being set to nought and moved to the account's dust"
    source: "`nexus/infrastructure/praxis_connector/outcome_processor.py` 562-580"
  - claim: "A release refused leaves the position as it was, the fill ending as a failure"
    source: "`nexus/core/capital_controller/capital_controller.py` 769-782 and 784-798, the return at `nexus/infrastructure/praxis_connector/outcome_processor.py` 248-253"
  - claim: "A position whose cost basis is nought, or which belongs to another strategy, has no release worked out and is reduced with no money moved"
    source: "`nexus/infrastructure/praxis_connector/outcome_processor.py` 422-423 and 426-437, reduced at 256-258"
  - claim: "A nought cost basis is read before the fill is weighed against the position, so an oversize fill on one still raises"
    source: "`nexus/infrastructure/praxis_connector/outcome_processor.py` 422-423 before 424-425, raised at 516-521"
  - claim: "A fill naming no trade, naming one with no position, or bigger than the position raises before anything is written"
    source: "`nexus/infrastructure/praxis_connector/outcome_processor.py` 503-511 and 516-521 before 558-560"
  - claim: "The profit reported is the fill's price against the position's entry price over the size sold, signed the other way for a position sold short, and the exit's own fees taken off that"
    source: "`nexus/infrastructure/praxis_connector/outcome_processor.py` 523-525 then 533"
  - claim: "The money given back is the position's cost basis over the size sold, a different figure counting the entry's fees"
    source: "`nexus/infrastructure/praxis_connector/outcome_processor.py` 438, released at 242-247"
  - claim: "A release inside the rounding margin of what the account or the strategy holds is trimmed to the smaller of the three"
    source: "`nexus/core/capital_controller/capital_controller.py` 800-806, reached only past the refusals at 769-798"
---
# What an exit outcome changes

An exit's fill is what closes a position, in whole or in part. It takes its size off the position, and the same off [what it has pending](when-an-entrys-position-grows.md) — or all of it, where less was pending. A position left at nothing is dropped from the record. Where a fill finishes the order, was meant to close the position whole, and leaves some of it, that rest goes too: the remainder moves to the account's dust and the size to nothing.

## When the position does not move

A fill whose money could not be given back returns before the position is changed, and ends as a failure. One naming no trade raises, as does one naming a trade with no position, and so does one bigger than the position. One already seen, and one whose context names another command, are [turned back earlier still](what-an-entry-outcome-changes.md).

Where no release is worked out at all — the cost basis being nought, or the position belonging to another strategy — a fill within the position reduces it with no money moved. A nought basis is read before the fill is weighed against the position, so an oversize fill on one still raises.

## The two figures an exit is worth

The profit reported is the fill's price against the position's entry price, over the size sold, with the sign turned for a position sold short. The exit's own fees come off that figure, either way round.

The money given back is a different figure: the cost basis over the size sold, which counts the entry's fees as well. A release past what the account or the strategy holds is refused; one over by no more than a rounding margin is trimmed to the smallest of the three.

## Related

- [When an entry's position grows](when-an-entrys-position-grows.md)
- [What an entry outcome changes](what-an-entry-outcome-changes.md)
- [How Nexus sets money aside](how-nexus-sets-money-aside.md)

---

Created 2026-10-18 19:00 UTC · Last modified 2026-10-23 09:00 UTC
