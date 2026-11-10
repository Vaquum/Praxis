---
row: P179-01
baseline: 49aa659
created: 2026-11-09 13:28 UTC
modified: 2026-11-09 13:28 UTC
evidence:
  - claim: "A change that started is remembered with its phase at cancelling"
    source: "`execution_manager.py` 1253, then 1254, then 1255"
  - claim: "A plan recorded for it moves that phase to placing and keeps the start beside it"
    source: "`execution_manager.py` 1257, then 1258, then 1259, then 1261 into 1262"
  - claim: "A state-unknown sets the remembered phase to whichever the record carried"
    source: "`execution_manager.py` 1264, then 1265, then 1267 into 1268-1270"
  - claim: "A completed change records the generation, the settings from its own start and the size from its plan"
    source: "`execution_manager.py` 1272, then 1273, then 1274, then 1275, then 1276-1283, then 1285 into 1286-1288"
  - claim: "It is recorded only where that start was found in the replay"
    source: "`execution_manager.py` 1285, against 1281"
  - claim: "The size stands at nought where no plan was found"
    source: "`execution_manager.py` 1275"
  - claim: "A completed change and an abandoned one both forget the change in flight"
    source: "`execution_manager.py` 1290, or 1292, then 1293"
---
# How a replay works out where a ladder's change had got to

Reading the record back builds two things about each ladder's grid changes: the change still in flight, if any, and the last change that completed.

## The change in flight

A change that started is remembered with its phase at cancelling. A plan recorded for it moves that phase to placing, keeping the start beside it. A state-unknown sets the phase to whichever the record carried, which is how a change that halted comes back at the step it halted on.

A completed change forgets it, and so does an abandoned one. Either way the ladder has no change owing.

## The last completed change

Its generation, the settings from its own start, and the size from its plan.

It is recorded only where that start was found in the replay. A completion whose start fell outside the window read leaves no completed grid at all, and [the resuming](what-a-resumed-ladders-grid-is-taken-from.md) then falls back to the ladder's first grid.

The size stands at nought where no plan was found, so a completion recorded without its plan gives a grid of no rungs.

## Related

- [What a resumed ladder's grid is taken from](what-a-resumed-ladders-grid-is-taken-from.md)
- [Which ladders a restart passes over](which-ladders-a-restart-passes-over.md)
- [How a restart reads its record back](how-a-restart-reads-its-record-back.md)
