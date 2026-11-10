---
row: N9-02
baseline: 49aa659
created: 2026-11-03 15:40 UTC
modified: 2026-11-09 10:25 UTC
evidence:
  - claim: "Both records the store writes are stamped with the machine's own clock, read as the record is built"
    source: "`nexus/infrastructure/state_store.py` 202 and 240"
  - claim: "The store is built with no clock to read, Praxis handing it a path and nothing besides"
    source: "`nexus/infrastructure/state_store.py` 106-117, given a path alone at `praxis/launcher.py` 4073"
  - claim: "The clock Praxis is built with is handed to the capital controller, the checks and the mode controller as each is built, and the store is not among them"
    source: "`praxis/launcher.py` 2782 handed on at 4100, 4118 and 4130, reading the moment at 205, against 4073"
  - claim: "A replay's own records are never cut at all, the checkpoint its start may make falling before any of them is written and no other caller being reached"
    source: "`praxis/replay/run_replay.py` 150 reaching `nexus/startup/sequencer.py` 481 under the test at 472 through `praxis/launcher.py` 4085, all of it before `praxis/replay/run_replay.py` 163, against the timer's start at `praxis/launcher.py` 4675 and the stopping sequence at 4030, neither of them reached on a replay"
---
# Which clock a record is stamped off

Every record [the log](how-a-record-reaches-the-log.md) holds is stamped with the machine's own clock, read at the moment the record is built.

## Why that holds on every host

The store that stamps them is built with no clock to read. Praxis hands it a path and nothing besides, so there is no other clock for it to reach.

## What a replay's records carry

[A replay](replay.md) is driven by [a clock made up for the run](the-replay-clock.md). Praxis hands the clock it was built with to the capital controller, the checks and the mode controller as it builds each of them, so on a replay those are built on the made-up time.

The store is not among them, so its records carry machine time while the parts handed that clock carry the run's.

## What a replay's log keeps

All of it. [The cut](what-the-thirty-day-cut-leaves.md) runs only at a checkpoint, and [the one checkpoint a replay can reach](which-hosts-the-checkpoint-timer-runs-on.md) is its start's, which comes before any record is written. So nothing a replay writes is ever weighed against a cutoff at all.

## Related

- [How a record reaches the log](how-a-record-reaches-the-log.md)
- [The replay clock](the-replay-clock.md)
- [What the thirty-day cut leaves](what-the-thirty-day-cut-leaves.md)
