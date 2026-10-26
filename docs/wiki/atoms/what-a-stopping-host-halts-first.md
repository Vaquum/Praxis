---
row: N6-01
baseline: 49aa659
created: 2026-10-26 16:00 UTC
modified: 2026-10-26 20:00 UTC
evidence:
  - claim: "The launcher calls the stop on three other Nexus loops and one watch of its own before the stopping sequence is built or run at all"
    source: "`praxis/launcher.py` 4004-4007 before 4009 and 4030, the three called at `nexus/core/health_loop.py` 98-102, `nexus/core/mtm_loop.py` 136-140 and `nexus/infrastructure/snapshot_scheduler.py` 92-96"
  - claim: "The four things the sequence keeps are emptied first, which matters only to a sequence run twice, the launcher building a fresh one for each stop"
    source: "`nexus/startup/shutdown_sequencer.py` 178-181 against 166-168, built at `praxis/launcher.py` 4009 and run once at 4030"
  - claim: "The mode is set to halted before the sequence stops a loop of its own"
    source: "`nexus/startup/shutdown_sequencer.py` 183 before 184-186"
  - claim: "Where a mode controller is wired the setting goes through it, raising a hold named for the shutdown"
    source: "`nexus/startup/shutdown_sequencer.py` 219-221 into `nexus/core/mode_controller.py` 280 and 436-440"
  - claim: "The shutdown hold is one of the six whose being raised answers yes to the test for halting, and that answer takes the mode to halted, which the controller then writes"
    source: "`nexus/core/domain/operational_mode.py` 87-94, the test read at `nexus/core/mode_controller.py` 488-489 into 504-508"
  - claim: "Where no controller is wired the host writes the mode itself"
    source: "`nexus/startup/shutdown_sequencer.py` 222-227"
  - claim: "An entry, an exit or a change reaching the mode test in that window is refused there"
    source: "`nexus/core/validator/intake_stage.py` 361-384 reached at 442-444"
  - claim: "The loop asking for predictions is stopped next and the one running the timers after it, each passed over with a line where none is wired"
    source: "`nexus/startup/shutdown_sequencer.py` 184-185 into 238-243 and 252-257"
  - claim: "The loop reading outcomes has its stop called last"
    source: "`nexus/startup/shutdown_sequencer.py` 186 into 267-271"
---
# What a stopping host halts first

The stopping sequence Nexus runs sets its trading mode and calls a stop on three of its loops, in a fixed order, before it asks any strategy what it wants done.

## Before any of it

Three other Nexus loops — health, valuation and snapshots — are stopped by the launcher itself, along with a watch of its own. All four stops are called before the stopping sequence below is even built, and [what each leaves running](what-a-loops-stop-leaves-running.md) is a separate matter.

## The order the sequence runs in

The four things the sequence keeps are emptied, which matters only to a sequence run twice; the launcher builds a fresh one for each stop. Then the mode is set to halted. Where a mode controller is wired, the setting goes through it: a hold named for the shutdown is raised, and that hold is one of six whose being raised takes the mode to halted, which the controller writes. Where none is wired, the host writes the mode itself.

Then the loop asking for predictions, then the one running the timers — each passed over with a line where none is wired. Then [the loop reading outcomes](stopping-the-loop-that-reads-outcomes.md).

## Why the mode goes first

The setting lands before the loops stop, so an entry, an exit or a change reaching the mode test in that window is refused there — [what the halted mode turns away](what-the-halted-mode-turns-away.md).

## Related

- [What the halted mode turns away](what-the-halted-mode-turns-away.md)
- [What a loop's stop leaves running](what-a-loops-stop-leaves-running.md)

---

Created 2026-10-26 16:00 UTC · Last modified 2026-10-26 20:00 UTC
