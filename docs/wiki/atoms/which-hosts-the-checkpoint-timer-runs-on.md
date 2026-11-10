---
row: N9-01
baseline: 49aa659
created: 2026-11-03 15:40 UTC
modified: 2026-11-05 11:10 UTC
evidence:
  - claim: "Three calls ask a store for a checkpoint, and no such call stands anywhere else under `nexus/` or `praxis/`"
    source: "`nexus/infrastructure/snapshot_scheduler.py` 147, `nexus/startup/sequencer.py` 481 and `nexus/startup/shutdown_sequencer.py` 893"
  - claim: "The timer has one start, reached as the live host's per-account thread starts that account's loops"
    source: "`praxis/launcher.py` 4675, reached only from 3995 inside the body set as the thread's target at 3896, that thread started at 3902 from 2830"
  - claim: "Its stop runs on that same thread, after the wait the thread spends while the account runs"
    source: "`praxis/launcher.py` 4006 after the wait at 3999"
  - claim: "A replay builds the same runtime and starts no loops, so no turn of the timer falls while it runs"
    source: "`praxis/replay/run_replay.py` 147, 148, 150-151, 175 and 176 being every call it makes on the launcher, against the start reached only from `praxis/launcher.py` 3995"
  - claim: "It reaches no stopping checkpoint either, the sequence that asks for one running on the thread it never starts"
    source: "`praxis/replay/run_replay.py` 176 into `praxis/launcher.py` 3908 over a list filled only at 3901, against the sequence built at 4009-4029 and run at 4030 inside the body set as that thread's target at 3896"
  - claim: "Both hosts reach the start's reconciliation, the build handing it a connection out to Praxis"
    source: "`praxis/launcher.py` 3992, or `praxis/replay/run_replay.py` 150, into `praxis/launcher.py` 4075 handed over at 4082 before 4085, kept at `nexus/startup/sequencer.py` 113 and reaching 177 with the manifest loaded at 174 and assigned at 496 ahead of it, against the road out at 355-357"
---
# Which hosts the checkpoint timer runs on

Three calls ask a store for [a checkpoint](what-a-checkpoint-holds.md), and how a host was started decides which of them it can reach at all.

## The three callers

[A timer, a start and a stopping host](what-a-checkpoint-holds.md) — those three, and no fourth call asks for one anywhere in either package. Which of the three a host reaches is what differs, and [the timer](the-timer-that-checkpoints-while-a-host-runs.md) is the one that divides them.

## The live host

Praxis gives each account a thread of its own, and that thread starts the account's loops, the timer among them. The timer's single start sits there, and its stop on the same thread, after the wait the thread spends while the account runs.

## A replay

[A replay](replay.md) builds the same runtime and starts no loops, so no turn of the timer falls while it runs.

It reaches no stopping checkpoint either: the stopping sequence runs on that same per-account thread, and the thread list a replay's own shutdown walks is filled only where those threads are started.

What both hosts reach is the start. The build hands it a connection out to Praxis, so neither takes the road that passes the reconciliation over, and a replay's only checkpoint is the one its start may make — along with [whatever a failed one costs that start](what-a-failed-checkpoint-costs-a-start.md).

## Related

- [What a checkpoint holds](what-a-checkpoint-holds.md)
- [The timer that checkpoints while a host runs](the-timer-that-checkpoints-while-a-host-runs.md)
- [What a failed checkpoint costs a start](what-a-failed-checkpoint-costs-a-start.md)
