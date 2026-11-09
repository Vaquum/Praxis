---
row: N69-06
baseline: 49aa659
created: 2026-11-08 20:50 UTC
modified: 2026-11-08 20:50 UTC
evidence:
  - claim: "A restart's re-deriving takes the lock and empties the recovered shutdown hold outright, writing its three fields rather than going through the clearing that recomputes"
    source: "`nexus/core/mode_controller.py` 349, then 351-354, against 442-452"
  - claim: "So a shutdown hold that was saved by the last checkpoint does not survive into the restarted host"
    source: "`nexus/core/mode_controller.py` 352"
  - claim: "Both risk breakers are then evaluated from the recovered risk record, under that record's own lock or under none"
    source: "`nexus/core/mode_controller.py` 356-358"
  - claim: "A recompute is then made from everything recovered, and the waiting notification is drained outside the lock"
    source: "`nexus/core/mode_controller.py` 360, then 362"
  - claim: "It is not the only recompute, each hold the breakers move recomputing as it is moved"
    source: "`nexus/core/mode_controller.py` 357-358 reaching 434, or 440, or 446, or 452"
  - claim: "Nothing is seeded from the recovered mode itself, the health reading and the holds being what the recompute reads"
    source: "`nexus/core/mode_controller.py` 360 into 488-493"
  - claim: "No other hold is emptied outright, so a manual, reconciling or protection halt that outlived a stop is in force before anything resumes"
    source: "`nexus/core/mode_controller.py` 351-354 touching one hold alone"
  - claim: "The two risk holds are not left alone: the breakers that follow can clear the daily-loss one or set either"
    source: "`nexus/core/mode_controller.py` 357-358 into 392-396, and 398-412"
---
# What a restart re-derives

A host coming back up settles [its account's mode](how-the-mode-is-recomputed.md) once, before any work resumes, from what the snapshot gave it.

## The one hold that is thrown away

The recovered shutdown hold is emptied outright — its three fields written directly, rather than through the clearing that recomputes.

So a shutdown hold saved by the last checkpoint does not survive the restart. It belonged to the stopping that placed it, and a host recovering it would come up halted on a ground that no longer applies.

## The holds that are kept

No other hold is emptied outright.

So a manual, reconciling or protection halt that outlived a stop is in force before any startup work drains, rather than being discovered partway through.

The two risk holds are a separate matter: the breakers that run next can move them.

## The breakers

Both are then evaluated from the recovered risk record, under that record's own lock or under none where that lock is this one.

So a loss that had decayed back under its limit while the host was down lifts the daily-loss hold here, and a drawdown hold is left on, that breaker never lifting itself.

## The recomputes

A recompute settles the mode from everything recovered, and the waiting notification is drained with the lock let go.

It is not the only one: each hold the breakers move recomputes as it is moved, so the last recompute confirms a mode the earlier ones may already have reached.

Nothing is seeded from the recovered mode itself. The health reading and the holds are what the recompute reads, so the mode a restarted host runs under is derived rather than restored.

## Related

- [How the mode is recomputed](how-the-mode-is-recomputed.md)
- [What setting a hold that already stands does](what-setting-a-hold-that-already-stands-does.md)
