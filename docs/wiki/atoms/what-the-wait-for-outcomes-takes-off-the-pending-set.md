---
row: N83-02
baseline: 49aa659
created: 2026-11-09 04:19 UTC
modified: 2026-11-09 04:19 UTC
evidence:
  - claim: "A wait with no road inbound, or no span to wait for, answers with the whole set it was given"
    source: "`nexus/startup/shutdown_sequencer.py` 643 into 644"
  - claim: "A wait with nothing pending answers before any of that"
    source: "`nexus/startup/shutdown_sequencer.py` 619 into 620"
  - claim: "The waiting works on a copy of the set, and against a deadline taken from the clock as the wait begins"
    source: "`nexus/startup/shutdown_sequencer.py` 646, and 647"
  - claim: "The round is entered only while something remains and the deadline has not passed"
    source: "`nexus/startup/shutdown_sequencer.py` 649"
  - claim: "A round where nothing arrived begins again at once"
    source: "`nexus/startup/shutdown_sequencer.py` 652-653"
  - claim: "An outcome for a command not in the set is handed to another road and the round begins again"
    source: "`nexus/startup/shutdown_sequencer.py` 655 into 656-657"
  - claim: "A fill and an ending are both applied, and only an ending takes its command off the set"
    source: "`nexus/startup/shutdown_sequencer.py` 659-660, against 662-663"
  - claim: "What is left of the copy is answered, however the round was left"
    source: "`nexus/startup/shutdown_sequencer.py` 670"
---
# What the wait for outcomes takes off the pending set

A stopping host waits for the commands it is still owed answers on, and gives back the ones it never got.

## The two ways it waits for nothing

No road inbound, or no span to wait for. Either answers with the whole set it was given, so a host built without an inbound road treats every pending command as unanswered.

## Nothing to wait for

A wait with nothing pending answers before any of that — no deadline taken, no clock read.

## The copy and the deadline

The waiting works on a copy of the set, and against a deadline taken from the clock as the wait begins. The round is entered only while something remains and that deadline has not passed.

So the deadline is weighed before an outcome is taken, not after one is applied. The applying of the last outcome can run past it.

## What each outcome does

A round where nothing arrived begins again at once, so the waiting is a busy one: it asks again immediately rather than sleeping.

One that names a command not in the set is handed to another road, and the round begins again. One that names a command in the set is applied if it is a fill or an ending.

Only an ending takes its command off the set. A fill is applied and the command stays — so a partly filled command still holds the wait open until something ends it or the deadline passes.

## The answer

What is left of the copy, however the round was left. A set answered empty means every command ended; anything in it was never answered.

## Related

- [What a stopping host halts first](what-a-stopping-host-halts-first.md)
- [What a sequencer refuses to be built with](what-a-sequencer-refuses-to-be-built-with.md)
