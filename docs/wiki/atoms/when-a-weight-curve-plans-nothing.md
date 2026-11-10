---
row: P4-52
baseline: 49aa659
created: 2026-10-14 08:50 UTC
modified: 2026-10-14 08:50 UTC
evidence:
  - claim: "With the venue's step known, each part but the last is rounded down to it and a part that rounds to nothing is refused as the plan is made"
    source: "`praxis/core/plan_weighted_slices.py` 66-72"
  - claim: "The last part takes what the others left, rounded down, and nothing left for it is refused too"
    source: "`praxis/core/plan_weighted_slices.py` 76 and 78-83"
  - claim: "With no step known, the parts are the weights against the whole and the last is the plain remainder, neither rounded nor weighed, so a weight that vanishes as the two are added plans nothing"
    source: "`praxis/core/plan_weighted_slices.py` 58-62"
  - claim: "An amount at or below nought is refused only later, as the order's intent is built"
    source: "`praxis/core/domain/events.py` 197-203, reached from `execution_manager.py` 5960"
---
# When a weight curve plans nothing

[A weighted run](work-fed-out-over-time.md) splits an amount across its parts by the weights given. Whether a part that comes to nothing is caught depends on whether the venue's sizes are known at the time the split is made.

## With the venue's sizes known

Each part but the last is rounded down to the venue's step, and one that rounds away to nothing is refused there and then: the run is turned away rather than started with a part nobody can send.

The last part takes whatever the others left, rounded down the same way. Nothing left for it is refused too, so a curve whose weights eat the whole amount before the end cannot start either.

## With them unknown

Without a step to round to, the parts are simply each weight against the whole amount, and the last is the plain remainder. Neither is checked for being above nought.

A curve that passes every settings check can therefore plan a part of nothing. The weights only have to be above nought and add to one, and a second weight small enough to vanish into the first as they are added satisfies both — then works out as nothing at all against the amount.

## Where it surfaces instead

That part is caught on the way out, as the order's own instruction is built: an amount at or below nought is refused there. So the run starts, works through its parts, and fails when it reaches the one that came to nothing — rather than being turned away at the start.

## Related

- [Work fed out over time](work-fed-out-over-time.md)
- [The settings each way of working takes](the-settings-each-way-of-working-takes.md)
- [The sizes a venue trades in](the-sizes-a-venue-trades-in.md)

---

Created 2026-10-14 08:50 UTC · Last modified 2026-10-14 08:50 UTC
