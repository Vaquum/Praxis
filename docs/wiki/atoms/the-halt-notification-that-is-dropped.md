---
row: N69-05
baseline: 49aa659
created: 2026-11-08 20:50 UTC
modified: 2026-11-08 20:50 UTC
evidence:
  - claim: "A change into halted records the blame as a notification waiting to be made"
    source: "`nexus/core/mode_controller.py` 510-511"
  - claim: "Draining takes that blame and clears it under the lock, and reads whether the mode is still halted"
    source: "`nexus/core/mode_controller.py` 371-374"
  - claim: "The blame is cleared whether or not the notification is made"
    source: "`nexus/core/mode_controller.py` 373, standing before the three reasons to answer at 376"
  - claim: "Nothing is fired where no blame was waiting, where the mode is no longer halted, or where no callback was given"
    source: "`nexus/core/mode_controller.py` 376-377"
  - claim: "So a halt lifted before the draining ran loses its notification, rather than having it kept for later"
    source: "`nexus/core/mode_controller.py` 373 ahead of 376"
  - claim: "The callback is called outside the lock, and an ordinary failure of it is logged and goes no further"
    source: "`nexus/core/mode_controller.py` 379-382, the lock let go at 374"
  - claim: "A note is left only where the mode changed into halted, so a further hold placed on an account already halted leaves the first note standing"
    source: "`nexus/core/mode_controller.py` 510, reached only where 496 found a change"
  - claim: "Only one note is held, so a second note can displace the first only after the mode has left halted and returned to it"
    source: "`nexus/core/mode_controller.py` 511, writing over one field"
---
# The halt notification that is dropped

A mode changing into halted leaves a note of what drove it, and something else fires the alert later. Between the two, the note can be lost.

## What is left and what takes it

The recomputing records the blame as a notification waiting to be made.

Draining takes that blame and clears it under the lock, and reads at the same moment whether the mode is still halted.

## Cleared either way

The blame is cleared before any of the three reasons to do nothing is read.

So a drain that decides not to fire has still taken the note. Nothing is fired where no note was waiting, where the mode is no longer halted, or where no callback was ever given.

## What that costs

A halt lifted between the halting and the draining loses its alert altogether. The note is not kept for later and not fired late — it is taken and discarded, and nothing records that an alert was skipped.

## One note at a time

A note is left only where the mode changed into halted. A further hold placed on an account already halted changes no mode, so no note is left and the first one stands — whatever ground the new hold was.

The field holds one note, so a second can displace the first only where the mode has left halted and come back to it before the draining ran.

## Outside the lock

The callback is called with the lock let go, and an ordinary failure of it is logged and goes no further. A caller's failing alert cannot stop the mode being controlled.

## Related

- [How the mode is recomputed](how-the-mode-is-recomputed.md)
- [Why the health tick commits in one hold of the lock](why-the-health-tick-commits-in-one-hold-of-the-lock.md)
