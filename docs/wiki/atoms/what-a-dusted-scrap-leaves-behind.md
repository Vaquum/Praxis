---
row: N3-06
baseline: 49aa659
created: 2026-10-22 16:40 UTC
modified: 2026-10-23 07:08 UTC
evidence:
  - claim: "A fill against a position being sold has its own part taken out of the deployed figures before the remainder is dusted"
    source: "`nexus/infrastructure/praxis_connector/outcome_processor.py` 241-247, ahead of 576-580"
  - claim: "The amount asked for is the position's cost basis times the size of that fill"
    source: "`nexus/infrastructure/praxis_connector/outcome_processor.py` 438"
  - claim: "Nothing is asked for where the sale is unnamed, the position is not there, its cost basis is nought, the fill is larger than it, or it belongs to another strategy"
    source: "`nexus/infrastructure/praxis_connector/outcome_processor.py` 415-437"
  - claim: "What comes out can be less than was asked for, either figure capping it, and a strategy left within a millionth of a millionth of nought is dropped rather than kept at a remainder"
    source: "`nexus/core/capital_controller/capital_controller.py` 800-806 into 1097-1098, dropped at 1100-1113, the amount at `nexus/core/domain/capital_state.py` 16"
  - claim: "Dusting the remainder changes neither deployed figure and takes the position out of the record: the lines doing it write the dust, the size and the deletion, and ask the money figures for nothing"
    source: "`nexus/infrastructure/praxis_connector/outcome_processor.py` 576-580 into 594-595, and 696-702"
  - claim: "Where nothing is asked for, nothing comes out of either figure"
    source: "`nexus/infrastructure/praxis_connector/outcome_processor.py` 243 against 244-247"
  - claim: "A close the venue refuses before an order exists reaches none of that, the taking-out being reached only from a fill being reported"
    source: "`praxis/launcher.py` 1323 into 1363-1367, returning at 1369 before an order is built, against `nexus/infrastructure/praxis_connector/outcome_processor.py` 224 and 242-247"
---
# What a dusted scrap leaves behind

A scrap moved to the dust leaves the money it was bought with counted as deployed, with no position behind it in Nexus's record.

## The road that fills

A fill against a position being sold has its own part taken out of the deployed figures first: the position's cost basis times the size of that fill, worked out while the position is still whole. Only then is [the remainder dusted](where-a-positions-last-scraps-go.md). What is left standing is the scrap's share of the cost basis. Where [what came out](what-a-taking-out-takes.md) was capped by a figure, both figures lose that same smaller amount instead, and of the strategy's there may be nothing left at all, a figure near enough nought being dropped rather than kept.

Five things stop the asking: an unnamed sale, a position that is not there, a cost basis of nought, a fill larger than the position, and a position belonging to a different strategy from the one reporting. Where it is stopped nothing comes out of either figure, so the whole position's cost basis stays standing instead.

[How much comes out](what-a-taking-out-takes.md) is a question of its own.

## The road with no order

A close the venue refuses before an order exists reaches none of that: the taking-out is reached only from a fill being reported. The whole position's cost basis stays standing.

## What a start does with it

[What a start does with it](what-a-start-does-with-a-dusted-position.md) is a question of its own.

## Related

- [Where a position's last scraps go](where-a-positions-last-scraps-go.md)
- [What a boot rebuilds from the positions](what-a-boot-rebuilds-from-the-positions.md)

---

Created 2026-10-22 16:40 UTC · Last modified 2026-10-23 07:08 UTC
