---
row: P175-01
baseline: 49aa659
created: 2026-11-09 12:59 UTC
modified: 2026-11-09 12:59 UTC
evidence:
  - claim: "An equal-slice scheme's settings are rebuilt from the count of parts and the gap between them"
    source: "`execution_manager.py` 539, then 540-542"
  - claim: "A weighted one is rebuilt from the gap and the weights the start recorded"
    source: "`execution_manager.py` 544, then 545-547"
  - claim: "The weighted rebuild takes no count of parts, where the equal-slice one does"
    source: "`execution_manager.py` 545-547, against 540-542"
  - claim: "Any other mode is refused as not resumable, with the mode named in the refusal"
    source: "`execution_manager.py` 549, then 550"
  - claim: "All three figures were recorded on the start, so the command's own settings need not survive"
    source: "`execution_manager.py` 5758-5775, the three set at 5767, and 5768, and 5770-5774"
---
# What a scheme's settings are rebuilt from

The settings of [work fed out over time](work-fed-out-over-time.md) are rebuilt after a restart from what the start recorded, not from the command that asked for it.

## Two modes, two rebuilds

An equal-slice scheme's settings come from the count of parts and the gap between them. Those two figures are the whole of such a schedule.

A weighted one's come from the gap and the weights the start recorded. It takes no count of parts: the weights are one per part, so the count is in them.

## What cannot be rebuilt

Any other mode is refused as not resumable, with the mode named in the refusal.

## Why the command need not survive

All three figures — the count, the gap and the weights — were recorded on the start itself. So the command that asked for the work can be gone, and the schedule still comes back exactly as it was.

## Related

- [Work fed out over time](work-fed-out-over-time.md)
- [What a resumed scheme comes back holding](what-a-resumed-scheme-comes-back-holding.md)
- [What stops a scheme being resumed](what-stops-a-scheme-being-resumed.md)
