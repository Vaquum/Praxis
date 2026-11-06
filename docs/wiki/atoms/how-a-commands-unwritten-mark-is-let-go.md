---
row: P5-01
baseline: 49aa659
created: 2026-11-05 16:22 UTC
modified: 2026-11-06 06:59 UTC
evidence:
  - claim: "A write that went down drops the mark of every command the copy taken before it holds whose number still matches"
    source: "`praxis/launcher.py` 4426-4427 before 4439, the copy walked at 4459-4460 and dropped at 4461-4462 under the test at 4461"
  - claim: "Each mark is set with a number one higher than the last"
    source: "`praxis/launcher.py` 2940 before 2941-2943"
  - claim: "A write that raises enters no drop at all, the branch holding the walk never reached"
    source: "`praxis/launcher.py` 4440-4441 against the `else` at 4449"
  - claim: "That same failure raises nothing out of the handling, which goes on to answer its caller"
    source: "`praxis/launcher.py` 4440-4441, which raises nothing, so 4464 is reached after it and 4467 answers"
  - claim: "The write an operator's halt or resume asks for drops no mark"
    source: "`praxis/launcher.py` 3549 against 4439, both reaching `nexus/infrastructure/state_store.py` 199 and 206, with nothing from `praxis/launcher.py` 3548 to 3552 reaching the mapping 4461-4462 drops from"
---
# How a command's unwritten mark is let go

An unwritten mark is a note the host keeps against a command, and the write asked for after an outcome is what lets it go.

## What drops it

Marks go in bulk. Before a write is attempted every mark then standing is copied, and once the write returns that copy is walked, each mark in it being dropped where the number standing against the command still matches the one copied. So the write asked for after one command's outcome lets go of marks belonging to other commands.

## The number each mark carries

Each mark is set with a number one higher than the last. A command marked afresh between the copy and the walk therefore stands against a newer number than the copy holds, and keeps its mark through a write that dropped its neighbours'.

## What a failed write leaves

A write that raises never reaches the walk, so every mark stays. The failure raises nothing out of the handling either: the call carries on and answers its caller.

## The write that drops none

The write [an operator's halt or resume](which-of-a-hosts-changes-reach-the-log.md) asks for drops no mark at all.

## Related

- [Which of a host's changes reach the log](which-of-a-hosts-changes-reach-the-log.md)
- [Outcomes that never come back](outcomes-that-never-come-back.md)
