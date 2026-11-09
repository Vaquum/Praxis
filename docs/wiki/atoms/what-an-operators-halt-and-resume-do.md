---
row: P130-02
baseline: 49aa659
created: 2026-11-15 09:30 UTC
modified: 2026-11-15 09:30 UTC
evidence:
  - claim: "Halting and resuming are one routine, told which it is by a flag"
    source: "`launcher.py` 3513, and 3516"
  - claim: "It weighs the caller and answers with whatever refusal that gives"
    source: "`launcher.py` 3519, then 3521 into 3522"
  - claim: "It then resolves the account, answers with whatever refusal that gives, and reads the account's name off the runtime"
    source: "`launcher.py` 3524, then 3526 into 3527, or 3531"
  - claim: "The reason is read from the body, with a default standing in for an empty body, a body that will not parse, a body that is not a mapping, and a reason that is absent or blank"
    source: "`launcher.py` 3468, then 3470 into 3471, or 3473-3474 into 3475 into 3476, or 3478, then 3480"
  - claim: "Halting sets a manual halt carrying that reason and builds one record of the ask; resuming clears the halt and builds the other"
    source: "`launcher.py` 3536 into 3537-3540, or 3543-3546"
  - claim: "The state is then written down, and a failure there answers an error at five hundred"
    source: "`launcher.py` 3548-3549, then 3550 into 3552"
  - claim: "The record of the ask is appended only where the host has a record at all, and a failure there is reported and no more"
    source: "`launcher.py` 3554, then 3555-3558, then 3559"
  - claim: "The alert sink is told at warning, carrying the account and the reason"
    source: "`launcher.py` 3562-3565"
  - claim: "The answer is the same body the status road gives"
    source: "`launcher.py` 3567, and 3510, both from 3483-3495"
---
# What an operator's halt and resume do

Halting an account and letting it go again are one routine, told which it is by a flag, and the two differ only in what they set and which record they write.

## Getting to the account

[The caller is weighed](what-every-operator-road-weighs-first.md), the account resolved, and its name read off the runtime rather than off the request.

## The reason

Read from the body of the ask, with a default standing in for every way of not giving one: an empty body, a body that will not parse, a body that is not a mapping, and a reason that is absent or is only blank space.

So an operator who sends nothing gets a reason recorded all the same, and it says which ask it was.

## The order of what follows

The mode is changed first — a manual halt set with that reason, or the halt cleared — and a record of the ask built.

The state is written down next, and a failure there answers an error at five hundred. The change is already in memory by then, so an operator told the ask failed is looking at an account that has been halted and may not stay halted past a restart.

The record of the ask is appended after, and only where the host has a record at all. A failure there is reported and no more, so the audit of who asked is the one part of this that may quietly be missing.

The alert sink is told at warning, and the answer is the same body the status road gives.

## Related

- [What every operator road weighs first](what-every-operator-road-weighs-first.md)
- [Alerts](alerts.md)
- [Protection](protection.md)
