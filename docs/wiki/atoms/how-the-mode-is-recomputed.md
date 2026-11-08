---
row: N69-01
baseline: 49aa659
created: 2026-11-13 01:30 UTC
modified: 2026-11-13 01:30 UTC
evidence:
  - claim: "Any halting hold standing, or a health reading of halted, gives halted"
    source: "`nexus/core/mode_controller.py` 488-489"
  - claim: "Else any reduce-only hold standing, or a health reading of reduce-only, gives reduce-only"
    source: "`nexus/core/mode_controller.py` 490-491"
  - claim: "Else the health reading itself is the mode"
    source: "`nexus/core/mode_controller.py` 492-493"
  - claim: "Which input the mode is blamed on is then worked out, and where neither the mode nor that blame has changed nothing is written"
    source: "`nexus/core/mode_controller.py` 495-496, then 498-499"
  - claim: "A record is otherwise written whole, and the moment of transition is carried over unchanged where the mode itself did not change"
    source: "`nexus/core/mode_controller.py` 501-508"
  - claim: "A first recompute that leaves the mode where it started carries over the earliest moment there is, so the stamp marks no change at all until one happens"
    source: "`nexus/core/mode_controller.py` 502, carrying over whatever the record held"
  - claim: "The answer is whether the mode changed, so a recompute that writes a new blame and the same mode answers that nothing changed"
    source: "`nexus/core/mode_controller.py` 496, answered at 513"
  - claim: "A change into halted records the blame as a notification waiting to be made"
    source: "`nexus/core/mode_controller.py` 510-511"
---
# How the mode is recomputed

Every change to [an account's mode](ways-of-working-a-host-may-drive.md) goes through one recomputing, which reads the holds and the health reading and decides from them alone.

## The three steps

Any halting hold standing, or a health reading of halted, gives halted.

Failing that, any reduce-only hold standing, or a health reading of reduce-only, gives reduce-only.

Failing both, the mode is the health reading itself.

So a hold can only make the mode worse than the health reading, never better, and the health reading is what stands where nothing is held.

## What is written, and when

[Which input the mode is blamed on](which-hold-the-mode-is-blamed-on.md) is worked out next. Where neither the mode nor that blame has changed, nothing is written at all.

Otherwise a record is written whole: the mode, the blame, and a moment. The moment is the present one where the mode changed, and the one already recorded where only the blame did.

So past the first change of mode the stamp marks the last one. Before any change it is whatever the record began with — the earliest moment there is — which a first recompute changing only the blame carries straight over.

## What the answer means

The answer is whether the mode changed, not whether anything was written.

So a recompute that writes a fresh blame over an unchanged mode answers that nothing changed, having changed the record. A caller acting on that answer alone cannot tell the two apart.

## The notification

A change into halted records the blame as a notification waiting to be made, which [is fired outside the lock](the-halt-notification-that-is-dropped.md).

## Related

- [Ways of working a host may drive](ways-of-working-a-host-may-drive.md)
- [Which hold the mode is blamed on](which-hold-the-mode-is-blamed-on.md)
