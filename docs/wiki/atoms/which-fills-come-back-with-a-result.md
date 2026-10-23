---
row: N3-07
baseline: 49aa659
created: 2026-10-22 18:10 UTC
modified: 2026-10-22 18:10 UTC
evidence:
  - claim: "A fill against a position being entered comes back with no result"
    source: "`nexus/infrastructure/praxis_connector/outcome_processor.py` 448-451 into 256-260"
  - claim: "What it does instead is add the fill to the position's size and work its two prices out again across the whole of it"
    source: "`nexus/infrastructure/praxis_connector/outcome_processor.py` 479-490"
  - claim: "The account's money figures move for it all the same, that fill being reported to them before the position grows"
    source: "`nexus/infrastructure/praxis_connector/outcome_processor.py` 224-239 into `nexus/core/capital_controller/capital_controller.py` 955-957"
  - claim: "A fill against one being sold raises rather than returning where the sale is unnamed, the position is not there, or the fill is larger than the position"
    source: "`nexus/infrastructure/praxis_connector/outcome_processor.py` 503-505, 509-511 and 516-521"
  - claim: "The money figures are left as they were too: each of those three answers nothing when the release is worked out, and nothing is asked for where there is no answer"
    source: "`nexus/infrastructure/praxis_connector/outcome_processor.py` 415-425 into 243 against 244-247"
  - claim: "One caller logs the raise and goes on with the same report, handing it to the strategy and sending whatever that asks for; the other logs it and returns"
    source: "`nexus/core/outcome_loop.py` 404-408 into 410-425 and 433-437, against `praxis/launcher.py` 2918-2925"
  - claim: "A result that does come back is the gain less a fee figure the report carries"
    source: "`nexus/infrastructure/praxis_connector/outcome_processor.py` 533 into 597"
  - claim: "The gain is the price sold at less the price entered at, times the size sold, turned the other way round for a position held short, the cost basis being read nowhere in it"
    source: "`nexus/infrastructure/praxis_connector/outcome_processor.py` 523-525 into 533"
  - claim: "A result of nought is a result, the fill being read for whether it came back with one at all"
    source: "`nexus/infrastructure/praxis_connector/outcome_processor.py` 260"
---
# Which fills come back with a result

A result is what a sale came to, and a fill comes back with one only where it was selling.

## The fill that was buying

A fill against a position being entered adds itself to that position's size, works its two prices out again across the whole of it, and comes back with no result, so nothing is [written to the record](where-a-realized-result-is-written-down.md) for it. The account's money figures do move: the fill is reported to them first, before the position grows at all. A buy moves money and reports no gain or loss.

## The fill that was selling

A fill against a position being sold raises rather than returning where the sale is unnamed, where the position is not there to sell, or where the fill is larger than the position. Each of those stops the figures being moved, and no more. The raise reaches whichever caller made the report. One logs it and goes on with that same report, handing it to the strategy and sending what the strategy asks for; the other logs it and returns.

Where it does return, it returns a result: the price sold at less the price the position was entered at, times the size sold, turned the other way round for a position held short, and then less [a fee figure the report carries](what-a-fee-figure-is-worked-out-from.md). The cost basis does not come into it.

## Nought is an answer

A result of nought — a sale that came out even, or one whose gain the fees ate — is still a result. What is read is whether the fill came back with one at all, not what it came to, so an even sale is recorded like any other.

## Related

- [Where a realized result is written down](where-a-realized-result-is-written-down.md)
- [What an exit outcome changes](what-an-exit-outcome-changes.md)

---

Created 2026-10-22 18:10 UTC · Last modified 2026-10-22 18:10 UTC
