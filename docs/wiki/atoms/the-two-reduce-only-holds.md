---
row: N69-07
baseline: 49aa659
created: 2026-11-13 01:30 UTC
modified: 2026-11-13 01:30 UTC
evidence:
  - claim: "Two holds can ask for reduce-only alone: one for reconciling and one for protection"
    source: "`nexus/core/mode_controller.py` 540-542"
  - claim: "Either standing gives reduce-only, but only where no halting hold stands and the health reading is not halted"
    source: "`nexus/core/mode_controller.py` 490, reached only past 488"
  - claim: "Setting one that already stands leaves its reason and its moment as they were, and clearing one that does not stand touches nothing"
    source: "`nexus/core/mode_controller.py` 458-461, and 473-476"
  - claim: "A recompute is made either way, once, after the conditional rather than inside both arms of it"
    source: "`nexus/core/mode_controller.py` 463, and 478"
  - claim: "The answer is that recompute's, so it says whether the mode changed rather than whether the hold moved"
    source: "`nexus/core/mode_controller.py` 463 into 513, answered at 467"
  - claim: "Where a halting hold stands, placing a reduce-only one leaves the mode halted and answers that nothing changed"
    source: "`nexus/core/mode_controller.py` 463 into 488-489, answered at 467"
  - claim: "The waiting notification is drained after the lock is let go, as it is for a halting hold"
    source: "`nexus/core/mode_controller.py` 465, and 480, against 418 and 426"
---
# The two reduce-only holds

Besides the holds that halt an account outright, two can ask only that it stop opening new positions: one for reconciling and one for protection.

## What either does

Either standing gives reduce-only — but only where no halting hold stands and the health reading is not halted.

So a reduce-only hold is outranked by every halting hold. An account with both kinds standing is halted, and lifting the halting one is what lets the reduce-only one show.

## Setting and clearing

Setting one that already stands leaves its reason and its moment as they were. Clearing one that is already clear leaves it alone too. That is [the same shape the halting holds have](what-setting-a-hold-that-already-stands-does.md).

A recompute is made either way — once, after the conditional, rather than inside both arms of it. The outcome is the same and the writing is in one place.

## What the answer means

The answer is the recompute's, so it says whether the mode changed and not whether the hold moved.

Where a halting hold stands, placing a reduce-only one leaves the mode halted and answers that nothing changed, having placed the hold. It will matter later, when that halt lifts.

Where no halting hold stands and the record still reads halted — the record being rewritten only by a recompute — the same placing moves the mode to reduce-only and answers that it changed.

## The notification

Drained after the lock is let go, as it is for a halting hold. A reduce-only hold cannot itself halt anything, so what is drained is whatever a recompute left waiting.

## Related

- [How the mode is recomputed](how-the-mode-is-recomputed.md)
- [Which hold the mode is blamed on](which-hold-the-mode-is-blamed-on.md)
- [What setting a hold that already stands does](what-setting-a-hold-that-already-stands-does.md)
