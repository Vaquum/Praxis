---
row: N69-02
baseline: 49aa659
created: 2026-11-08 20:50 UTC
modified: 2026-11-08 20:50 UTC
evidence:
  - claim: "For halted, five grounds are weighed in a fixed order and the first standing is the blame: shutting down, manual, risk, reconciling, protection"
    source: "`nexus/core/mode_controller.py` 528-537"
  - claim: "The risk ground covers two holds under one name, so a daily-loss hold and a drawdown hold are blamed alike"
    source: "`nexus/core/mode_controller.py` 531"
  - claim: "For reduce-only, two grounds are weighed in order and the first standing is the blame: reconciling, protection"
    source: "`nexus/core/mode_controller.py` 540-546"
  - claim: "Anything else is blamed on health, including a halted mode with no hold standing"
    source: "`nexus/core/mode_controller.py` 548, reached where no ground held"
  - claim: "A health reading of halted with a hold standing as well is blamed on the hold, the health reading going unnamed"
    source: "`nexus/core/mode_controller.py` 535-537, reached before 548"
  - claim: "The order is by ground rather than by when a hold was placed, so an earlier hold of a lower ground is never the blame while a higher one stands"
    source: "`nexus/core/mode_controller.py` 535-537, reading the order it was given"
---
# Which hold the mode is blamed on

Every mode [the recomputing settles](how-the-mode-is-recomputed.md) is recorded together with one word saying what drove it, and several holds standing at once give one word.

## Halted

Five grounds are weighed in a fixed order, and the first one standing is the blame: shutting down, manual, risk, reconciling, protection.

The risk ground covers two holds under one name. A daily-loss hold and a drawdown hold are therefore blamed alike, and the record cannot say which of the two it was.

## Reduce-only

Two grounds, in order: reconciling, then protection.

## Everything else

Blamed on health — which is right where the health reading is what gave the mode, and is also what a halted mode with no hold standing is blamed on.

A health reading of halted with a hold standing as well is blamed on the hold. The reading still demanded the halt; the word simply never says so.

## The order the grounds stand in

The order is over grounds rather than over when each hold was placed.

So a manual hold placed hours ago is the blame over a reconciling hold placed a second ago, and a reconciling hold placed first is not the blame while a manual one stands. A reader of the word learns which ground is highest among those standing, and nothing about which came first.

## What lifting the highest does

It moves the blame to the next ground standing. Where that ground is another halting one the mode is unchanged, and [a change of blame alone is one the recomputing writes without reporting](how-the-mode-is-recomputed.md).

Where the only grounds left are reduce-only ones, the mode moves to reduce-only — so lifting the last halting hold does change the mode, without making the account free.

## Related

- [How the mode is recomputed](how-the-mode-is-recomputed.md)
- [Ways of working a host may drive](ways-of-working-a-host-may-drive.md)
