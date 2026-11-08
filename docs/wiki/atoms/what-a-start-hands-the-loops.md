---
row: N72-05
baseline: 49aa659
created: 2026-11-13 03:30 UTC
modified: 2026-11-13 03:30 UTC
evidence:
  - claim: "One binding is made per strategy the manifest names, carrying that strategy's name, its series, its interval and its label"
    source: "`nexus/startup/sequencer.py` 608-616"
  - claim: "Nothing is read from disk and no model is rebuilt, the binding being made from the manifest's own fields"
    source: "`nexus/startup/sequencer.py` 608-616, reading only the spec"
  - claim: "A manifest that is not in hand stops the building with its own complaint"
    source: "`nexus/startup/sequencer.py` 605-606"
  - claim: "Timers are gathered per strategy, and a strategy with no timers is left out of the gathering altogether"
    source: "`nexus/startup/sequencer.py` 639-641"
  - claim: "The gathering of timers has a guard of its own for a manifest that is not in hand"
    source: "`nexus/startup/sequencer.py` 634-635"
  - claim: "What is gathered is the manifest's own run of timer records, carried through rather than rebuilt"
    source: "`nexus/startup/sequencer.py` 641"
  - claim: "The gathering is built fresh into a local name and written over the field, so whatever was held before is replaced rather than added to"
    source: "`nexus/startup/sequencer.py` 637, then 650"
  - claim: "The sequencer keeps both and offers each through a reading of its own, making no loop itself"
    source: "`nexus/startup/sequencer.py` 130, and 136, with no loop built in 596-650"
---
# What a start hands the loops

Starting a host works out two things the running system will need and builds neither of them into anything that runs.

## The bindings

One per strategy the manifest names, carrying that strategy's name, the series it reads, how often to read it, and a label.

Nothing is read from disk and no model is rebuilt. A binding is made out of the manifest's own fields, so what the poller is given is a description and not a connection.

A manifest that is not in hand stops the building with its own complaint, and the gathering of timers has a guard of its own for the same thing.

## The timers

Gathered per strategy. A strategy with no timers is left out of the gathering altogether, so what is handed over names only the strategies that have one.

What is gathered is the manifest's own run of timer records, carried through rather than rebuilt.

The gathering is built fresh into a local name and written over the field, so whatever was held before is replaced rather than added to.

## What this step does not do

It builds no loop. Both are kept and offered through a reading of their own, and what is made from them is made elsewhere.

## Related

- [Starting a host](starting-a-host.md)
- [What a strategy's startup answer does](what-a-strategys-startup-answer-does.md)
