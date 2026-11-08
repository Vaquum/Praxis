---
row: N72-04
baseline: 49aa659
created: 2026-11-13 03:30 UTC
modified: 2026-11-13 04:00 UTC
evidence:
  - claim: "A mode is read from the health figures where both a weigher and a reading of health were given"
    source: "`nexus/startup/sequencer.py` 671-672"
  - claim: "Where either is absent the mode is set to reduce-only, with a warning"
    source: "`nexus/startup/sequencer.py` 674-679"
  - claim: "Reduce-only is the narrower of the two answers it could have defaulted to"
    source: "`nexus/startup/sequencer.py` 675, set where 671 did not hold"
  - claim: "The mode is written into the health reading of the recovered state, where that state is in hand"
    source: "`nexus/startup/sequencer.py` 681-682"
  - claim: "That is the only field this step writes, the account's own mode being left as the recovery left it"
    source: "`nexus/startup/sequencer.py` 681-682, writing one field"
  - claim: "A strategy asked at startup is handed this mode in what it is given"
    source: "`nexus/startup/sequencer.py` 717 into 725"
---
# The mode a start begins with

Starting a host settles one mode before any strategy is asked, and settles it from health alone.

## Where it comes from

The health figures, weighed by the weigher — where both the weigher and a reading of health were given.

Where either is absent the mode is set to reduce-only, with a warning. Of the two answers it could have defaulted to, that is the narrower one: a host with no health reading begins in the state that allows less rather than more.

## Where it is written

The health reading of the recovered state, where that state is in hand.

That is the only field this step writes. The account's own mode is left as the recovery left it, so what this step settles is an input to the mode rather than the mode.

## Who sees it

A strategy asked at startup is handed this mode in what it is given.

So a strategy asked before health is known is told the account is in reduce-only. What follows from being told that — whether an answer opening a position is turned away, and where — is settled by [the checks an answer passes](the-order-the-intake-hooks-stand-in.md) rather than here.

## Related

- [What a strategy's startup answer does](what-a-strategys-startup-answer-does.md)
- [What a restart re-derives](what-a-restart-re-derives.md)
