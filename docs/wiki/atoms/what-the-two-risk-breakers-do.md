---
row: N69-08
baseline: 49aa659
created: 2026-11-08 20:50 UTC
modified: 2026-11-08 20:50 UTC
evidence:
  - claim: "The daily-loss breaker does nothing at all where no limit is set, neither placing its hold nor lifting it"
    source: "`nexus/core/mode_controller.py` 385-388"
  - claim: "Where a limit is set, the hold goes on for a loss standing strictly above it and is lifted for one at or below"
    source: "`nexus/core/mode_controller.py` 392-393, then 396"
  - claim: "The drawdown breaker weighs two limits, either of which may be unset, and places its hold where the figure stands strictly above the one it has"
    source: "`nexus/core/mode_controller.py` 400-405, and 407-412"
  - claim: "It has no lifting at all, so a hold it placed stays on until something outside the breakers lifts it"
    source: "`nexus/core/mode_controller.py` 398-412, which never clears"
  - claim: "Both breakers move their holds directly rather than through the roads that drain the notification"
    source: "`nexus/core/mode_controller.py` 393, or 396, or 403, or 410, against 415-418 and 423-426"
  - claim: "So the draining is the caller's to do, and the road that evaluates the breakers alone may be told to leave it"
    source: "`nexus/core/mode_controller.py` 331, which a caller may skip"
---
# What the two risk breakers do

Two breakers can halt an account on how badly it is doing, and they are built differently from each other.

## The daily loss

Where no limit is set the breaker does nothing at all — it neither places its hold nor lifts one already placed.

Where a limit is set, the hold goes on for a loss standing strictly above it, and is lifted for one at or below. A loss landing exactly on the limit therefore lifts the hold rather than keeping it.

So this breaker lifts itself as a loss decays, and an account halted by it can resume without anybody acting.

## The drawdown

It weighs two limits — one a share, one a sum — and either may be unset. The hold goes on where the figure stands strictly above whichever limit is there.

It has no lifting at all. A hold it placed stays on until [something outside the breakers lifts it](what-setting-a-hold-that-already-stands-does.md), so a recovered mark cannot resume trading by itself.

## How they move a hold

Directly, rather than through the roads that drain a waiting notification.

So the draining is left to whoever called the breakers, and the road that evaluates them alone can be told to leave it — which is how a caller holding its own lock keeps a callback from running under two.

## Related

- [What setting a hold that already stands does](what-setting-a-hold-that-already-stands-does.md)
- [The halt notification that is dropped](the-halt-notification-that-is-dropped.md)
