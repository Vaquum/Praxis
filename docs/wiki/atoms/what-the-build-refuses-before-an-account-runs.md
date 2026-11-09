---
row: P128-01
baseline: 49aa659
created: 2026-11-15 08:30 UTC
modified: 2026-11-15 08:30 UTC
evidence:
  - claim: "The build refuses where the trading stack or the host's loop is missing"
    source: "`launcher.py` 4067 into 4068-4069"
  - claim: "The settings and the state are read off the startup sequence after it has run, and the build refuses where either is absent"
    source: "`launcher.py` 4087, and 4088, then 4090 into 4091-4095"
  - claim: "The build refuses where the risk record has no slot to hold a lock"
    source: "`launcher.py` 4121 into 4122-4127"
  - claim: "Past that refusal the positions lock is put into that slot, so one lock stands under both names"
    source: "`launcher.py` 4102, then 4128"
  - claim: "A second lock of its own is made for the registry of commands"
    source: "`launcher.py` 4120"
  - claim: "The mode controller is built over the positions lock and reconciled at once"
    source: "`launcher.py` 4129-4133, then 4134"
  - claim: "Two handlers are built over that one controller, each taking its own answer from the settings"
    source: "`launcher.py` 4135-4137, and 4138-4140"
---
# What the build refuses before an account runs

Building an account's runtime is the step between its thread starting and its loops running, and what it refuses is never the account's own settings but something that should already be true around it.

## The host

The trading stack and the host's loop must both stand. Neither is built here, so a build reaching this point without them means the host started its accounts out of order.

## The startup sequence

The settings and the state are read off that sequence after it has run, and the build refuses where either is absent. So the sequence answering is not by itself proof that it produced anything, and the build says so rather than working with nothing.

## The slot for a lock

The risk record must have a slot able to hold a lock. Past that refusal the positions lock is put into it, so one lock stands under both names — the positions lock and the risk record's own.

A second lock, for the registry of commands, is made separately and stays separate.

## What is built once the refusals are past

The mode controller, over the positions lock, and reconciled at once rather than left until something asks. Then two handlers over that one controller — one for a disagreement found, one for a protection to put right — each taking its own answer from the settings.

So both handlers turn the same controller, and a deployment can choose what each of the two kinds of trouble does without choosing for the other.

## Related

- [Which of the store's writes take which locks](which-of-the-stores-writes-take-which-locks.md)
- [When an account can be delivered to](when-an-account-can-be-delivered-to.md)
- [The holds a report places](the-holds-a-report-places.md)
