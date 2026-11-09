---
row: P136-02
baseline: 49aa659
created: 2026-11-15 12:30 UTC
modified: 2026-11-15 12:30 UTC
evidence:
  - claim: "An amend still in flight sends the ladder down a road of its own, with the completed amend's parameters standing as its baseline"
    source: "`execution_manager.py` 1339, then 1340 into 1341-1343, then 1345-1353"
  - claim: "The generation before the one that was initiated is taken as the old one"
    source: "`execution_manager.py` 1417, then 1418"
  - claim: "The fixed plan is rebuilt from the planned record's three lists walked together, demanding they be of one length, and is nothing at all where no plan was recorded"
    source: "`execution_manager.py` 1420-1432"
  - claim: "The amend's own context is rebuilt from the initiation, carrying both generations, the old rung count, the prices, the weights and that plan, and is marked as having committed its cancel"
    source: "`execution_manager.py` 1433-1441"
  - claim: "The old generation's rungs still working are gathered by working their names out again"
    source: "`execution_manager.py` 1443-1445"
  - claim: "The new generation's are gathered the same way, over a grid sized from the highest place the plan names, and only where a plan was recorded"
    source: "`execution_manager.py` 1446, then 1447 into 1448, then 1449-1450"
  - claim: "Both sets together are the ladder's working children, and the cursor comes back as the old rung count"
    source: "`execution_manager.py` 1459, then 1458"
  - claim: "It comes back at the old generation, carrying the phase the history last recorded and that context"
    source: "`execution_manager.py` 1463, then 1464, then 1465"
---
# What a ladder amend caught mid-flight resumes as

An amend caught in flight by a restart is rebuilt as an amend still under way, so that the watchdog drives it on from where it stopped rather than starting it again.

## Which generation it comes back at

The old one — the generation before the one that was initiated. The ladder resumes as though the amend had not yet taken effect, carrying the phase the history last recorded for it.

The parameters it starts from are the last completed amend's, so an amend caught mid-flight builds on the grid before it rather than on the one it was replacing.

## Both grids at once

The old generation's rungs still working are gathered by working their names out again. The new generation's are gathered the same way, over a grid sized from the highest place the plan names — and only where a plan was recorded at all.

Both sets together are the ladder's working children. So a ladder resumes holding rungs from two grids, which is what the amend itself would have been holding.

## The context rebuilt

Both generations, the old rung count, the prices, the weights, and the fixed plan — the plan rebuilt from three recorded lists walked together under a demand that they be of one length, and nothing at all where no plan was recorded.

It is marked as having committed its cancel, so the resumed amend does not ask again whether the old grid may be retired.

## Related

- [How a ladder's rungs are found again](how-a-ladders-rungs-are-found-again.md)
- [How a ladder's prices are changed](how-a-ladders-prices-are-changed.md)
- [What one pass gathers for the schemes](what-one-pass-gathers-for-the-schemes.md)
