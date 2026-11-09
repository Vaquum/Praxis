---
row: P157-02
baseline: 49aa659
created: 2026-11-15 23:00 UTC
modified: 2026-11-15 23:00 UTC
evidence:
  - claim: "The venue's remembered rules give the lot step, the least amount and the least sum, with nothing standing in for the step and nought for both minimums where no rules are held"
    source: "`execution_manager.py` 9080, then 9081, then 9082, then 9083"
  - claim: "A remainder at or below nothing plans an empty grid"
    source: "`execution_manager.py` 9085 into 9086"
  - claim: "Otherwise the levels are worked out from the new parameters, the remainder and that step"
    source: "`execution_manager.py` 9088"
  - claim: "A level below the least amount, or worth less than the least sum at its own price, is passed over"
    source: "`execution_manager.py` 9090, then 9091 into 9092"
  - claim: "Each level that survives is numbered by how many have survived before it"
    source: "`execution_manager.py` 9089, then 9094"
---
# How a new ladder grid is renumbered

The grid an amend plans numbers its rungs by how many survived the venue's minimums, so the numbers run without gaps however many levels were dropped.

## What the minimums come from

The venue's remembered rules: the lot step, the least tradable amount, and the least tradable sum. Where no rules are held, nothing stands in for the step and nought for both minimums — which lets every level through.

## Which levels are dropped

Any below the least amount, and any worth less than the least sum at its own price. Each is simply passed over.

## The numbering

Each level that survives is numbered by how many have survived before it. So dropping the second of five levels leaves four rungs numbered without a gap, rather than four rungs keeping the numbers one, three, four and five.

That matters because a rung's name is [worked out from its number](how-a-ladders-rungs-are-found-again.md), and finding the rungs again walks the numbers from nothing upwards. A gap in the numbering would end that walk early.

## The empty grid

A remainder at or below nothing plans no levels at all. What the ladder does with an empty plan is settled by its caller rather than here.

## Related

- [How a ladder's rungs are found again](how-a-ladders-rungs-are-found-again.md)
- [What a ladder's start plans before it posts](what-a-ladders-start-plans-before-it-posts.md)
- [What a ladder's change is refused for](what-a-ladders-change-is-refused-for.md)
