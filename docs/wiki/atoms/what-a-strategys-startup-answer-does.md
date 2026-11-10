---
row: N72-01
baseline: 49aa659
created: 2026-11-08 21:25 UTC
modified: 2026-11-08 21:25 UTC
evidence:
  - claim: "Each strategy named in the manifest is asked in turn, and a strategy raising an ordinary failure there stops the whole starting with a complaint naming it"
    source: "`nexus/startup/sequencer.py` 719, then 727-735"
  - claim: "What it is handed at that moment carries an empty run of holdings, whatever the recovery found"
    source: "`nexus/startup/sequencer.py` 722-726, the holdings at 723"
  - claim: "The money it is told it has is the manifest's pool at that strategy's share of it"
    source: "`nexus/startup/sequencer.py` 720"
  - claim: "A strategy answering with nothing is passed over"
    source: "`nexus/startup/sequencer.py` 737-738"
  - claim: "An answer goes straight to the road for submitting where one was given at the building"
    source: "`nexus/startup/sequencer.py` 747-748"
  - claim: "An ordinary failure of that road is logged and the next strategy is asked, where the same failure from a strategy stops everything"
    source: "`nexus/startup/sequencer.py` 749-753, against 733-735"
  - claim: "Both catches name the ordinary kind of failure, so one of another kind passes either untouched"
    source: "`nexus/startup/sequencer.py` 733, and 749"
  - claim: "Where no road for submitting was given, the answer is added to a buffer kept per strategy"
    source: "`nexus/startup/sequencer.py` 740-745"
  - claim: "Three things must be in hand before any of this: the runner, the manifest and the mode"
    source: "`nexus/startup/sequencer.py` 708-709, and 711-712, and 714-715"
---
# What a strategy's startup answer does

Starting a host asks each strategy what it wants to do, and the answer takes one of two roads.

## What a strategy is asked with

An empty run of holdings, whatever the recovery found, and a share of the manifest's pool worked out from that strategy's percentage.

So what this step shows a strategy is no positions. Whether the strategy knows of any by then is settled by the steps before it — the restoring of its saved state and the handing over of its saved events — and not here.

## A strategy that fails

An ordinary failure from a strategy stops the whole starting, with a complaint naming that strategy.

## A road that fails

An ordinary failure of the submitting is logged, and the next strategy is asked.

So the same kind of failure is fatal to the boot from one side of those few lines and not from the other. Both catches name the ordinary kind, so a failure of another kind passes either of them untouched.

## Where the answer goes

Straight to the road for submitting, where one was given when the sequencer was built. Where none was, the answer is added to [a buffer kept per strategy](what-the-buffer-of-startup-answers-is-for.md) instead.

## What must be in hand first

The runner, the manifest and the mode. Each missing one stops the starting with its own complaint.

## Related

- [Starting a host](starting-a-host.md)
- [What the buffer of startup answers is for](what-the-buffer-of-startup-answers-is-for.md)
