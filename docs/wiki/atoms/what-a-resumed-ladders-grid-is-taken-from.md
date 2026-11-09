---
row: P173-02
baseline: 49aa659
created: 2026-11-09 13:28 UTC
modified: 2026-11-09 13:28 UTC
evidence:
  - claim: "A ladder with a change in flight is resumed through the change's own resumption"
    source: "`execution_manager.py` 1339, then 1340, then 1345-1346"
  - claim: "Otherwise the grid's generation, settings and size come from the last change that completed"
    source: "`execution_manager.py` 1355-1357"
  - claim: "Where no change ever completed, all three come from the start itself"
    source: "`execution_manager.py` 1356, naming what stands in"
  - claim: "The live children are found by walking that generation's grid by name"
    source: "`execution_manager.py` 1359-1361"
  - claim: "The place in the plan is set to how many of those names were posted"
    source: "`execution_manager.py` 1362-1376, the place set at 1367"
  - claim: "An ending still owing and a drain still owing its call-offs are carried onto the rebuilt work"
    source: "`execution_manager.py` 1378, then 1379-1381"
  - claim: "The work, its command, its acceptance and its trade are then all installed"
    source: "`execution_manager.py` 1383, then 1384, then 1385, then 1386"
---
# What a resumed ladder's grid is taken from

A ladder coming back after a restart needs to know which grid is live, and that comes from the last change to it that completed rather than from the start.

## The three figures

The generation, the settings and the size of the grid. Where no change ever completed, all three come from the start itself — the first grid is the start's own, and its generation is nought.

A ladder with a change in flight is resumed through [the change's own resumption](which-way-a-ladders-change-is-given-up.md) instead, which rebuilds what the change had reached.

## Finding the rungs again

The live children are found by walking that generation's grid by name, which is why the generation has to be right: a walk of the wrong generation finds none of the resting rungs.

The place in the plan is set to how many of those names were posted, so the ladder resumes counting from what it had already sent.

## What else is carried over

An ending still owing, and a drain still owing its call-offs. Then the work, its command, its acceptance and its trade are all installed, and the ladder is live again.

## Related

- [Which ladders a restart passes over](which-ladders-a-restart-passes-over.md)
- [How a ladder's rungs are found again](how-a-ladders-rungs-are-found-again.md)
- [What finishing a ladder's change adopts](what-finishing-a-ladders-change-adopts.md)
