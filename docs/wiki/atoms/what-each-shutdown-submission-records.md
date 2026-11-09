---
row: N83-04
baseline: 49aa659
created: 2026-11-09 04:19 UTC
modified: 2026-11-09 04:19 UTC
evidence:
  - claim: "Both submissions do nothing at all where either the road out or the configuration is missing"
    source: "`nexus/startup/shutdown_sequencer.py` 391 into 392, and 574 into 575"
  - claim: "A sent exit raises the position's pending sale by the size asked for, where the trade is named, the state is there and a size is known"
    source: "`nexus/startup/shutdown_sequencer.py` 445-448 into 455-458"
  - claim: "That raising happens under the positions lock, or under no lock at all where none was given"
    source: "`nexus/startup/shutdown_sequencer.py` 450-454 into 455"
  - claim: "A sent exit is kept under the name that came back, and that name is what goes on the list of what was sent"
    source: "`nexus/startup/shutdown_sequencer.py` 460, then 461"
  - claim: "The escalation of what is still pending meets those same two absences, and reports before it returns"
    source: "`nexus/startup/shutdown_sequencer.py` 780 into 781-785"
---
# What each shutdown submission records

A stopping host sends two kinds of thing, and each leaves a different trace behind.

## When neither is sent

Where either the road out or the configuration is missing, both submissions do nothing at all — no refusal, no report, no trace. A host built without a road out stops without asking anything of the far side.

## What an exit does on the way out

Where the trade is named, the state is there and a size is known, the position's pending sale is raised by the size asked for. That raising happens under the positions lock, or under no lock at all where the sequencer was given none.

## The name each keeps

An exit is kept under the name that came back from the far side, and that name is what goes on the list of what was sent.

[An abort's name on that list is its own](where-an-outcome-outside-the-wait-is-sent.md). So the list holds the far side's vocabulary for one kind of thing and this side's for the other, and a reader matching answers against it is matching against both at once.

## The escalation

The escalation of what is still pending meets those same two absences, and differs in one way: it reports before it returns. So the silent road is the sending, and the noisy one is the giving up.

## Related

- [What the wait for outcomes takes off the pending set](what-the-wait-for-outcomes-takes-off-the-pending-set.md)
- [The same absence in the two exit builders](the-same-absence-in-the-two-exit-builders.md)
