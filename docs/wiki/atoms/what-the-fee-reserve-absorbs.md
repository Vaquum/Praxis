---
row: N2-02
baseline: 49aa659
created: 2026-10-19 09:30 UTC
modified: 2026-10-22 12:00 UTC
evidence:
  - claim: "The fee reserve is one of five sums taken off the pool to leave what is free to commit"
    source: "`nexus/core/domain/capital_state.py` 109-116"
  - claim: "An entry fill whose actual fee came in under the estimate lifts the reserve by the difference, and one over lowers it"
    source: "`nexus/core/capital_controller/capital_controller.py` 924 and 957, reached for an entry alone at `nexus/infrastructure/praxis_connector/outcome_processor.py` 224-230"
  - claim: "A shortfall bigger than the reserve by more than a rounding margin refuses the entry fill's move, nothing being written"
    source: "`nexus/core/capital_controller/capital_controller.py` 926-938"
  - claim: "An exit's fill never reaches the reserve, its own fees coming off the profit it reports instead"
    source: "`nexus/infrastructure/praxis_connector/outcome_processor.py` 241-247 rather than 224-230, the fees at 533"
  - claim: "A reserve left within that margin of nothing is set to nothing"
    source: "`nexus/core/capital_controller/capital_controller.py` 959-960"
  - claim: "The same difference comes off what the strategy is recorded as having deployed"
    source: "`nexus/core/capital_controller/capital_controller.py` 962-963"
  - claim: "The reserve is written down and read back with the rest of the money record, a tiny negative clamped to nothing as it is read"
    source: "`nexus/infrastructure/wal_codec.py` 177 and 202"
---
# What the fee reserve absorbs

The fee reserve is money the account holds back for what trading costs. It is one of five sums taken off the pool to leave what is free to commit, alongside what positions, resting orders, sent orders and [money set aside](how-nexus-sets-money-aside.md) each hold.

## It is the gap between estimate and bill

An entry is sized with an estimate of its fees. Its fill reports what the fees actually came to, and the difference goes onto the reserve: a fill costing less than estimated lifts it, one costing more lowers it. The same difference comes off what the strategy is recorded as having deployed.

So the reserve is what the account carries for having guessed at an entry's costs: drawn down by entry fills that cost more than expected, topped back up by ones that cost less. An exit's fill never reaches it, that exit's fees coming off [the profit it reports](what-an-exit-outcome-changes.md) instead.

## Where it runs out

A shortfall bigger than the reserve by more than a rounding margin refuses [the entry fill's move](what-an-entry-outcome-changes.md) outright, and nothing is written — neither the position's money nor the fee figure.

A reserve left within that margin of nothing is set to nothing, so the figure does not drift on rounding alone.

## Where it lives

The reserve is written down and read back with the rest of the money record. A tiny negative is clamped to nothing as it is read, which is the same rounding margin applied on the way back in.

## Related

- [How Nexus sets money aside](how-nexus-sets-money-aside.md)
- [What an entry outcome changes](what-an-entry-outcome-changes.md)

---

Created 2026-10-19 09:30 UTC · Last modified 2026-10-22 12:00 UTC
