---
row: N84-01
baseline: 49aa659
created: 2026-11-13 18:30 UTC
modified: 2026-11-13 18:30 UTC
evidence:
  - claim: "The strategy's name must be text holding something other than spaces, and is then trimmed"
    source: "`nexus/core/capital_controller/capital_controller.py` 445 into 446-447, then 449"
  - claim: "The share must be a finite figure, and must stand above nought and at or below a hundred"
    source: "`nexus/core/capital_controller/capital_controller.py` 451 into 452-453, then 455 into 456-457"
  - claim: "The base is the pool multiplied by that share over a hundred"
    source: "`nexus/core/capital_controller/capital_controller.py` 459"
  - claim: "Without compounding, the base is the whole answer"
    source: "`nexus/core/capital_controller/capital_controller.py` 461-462"
  - claim: "The realized figure is weighed for being finite only where compounding is asked for"
    source: "`nexus/core/capital_controller/capital_controller.py` 464-467 into 468-472, standing after 461-462"
  - claim: "With compounding, the answer is the base plus that figure as it stands, sign and all"
    source: "`nexus/core/capital_controller/capital_controller.py` 474"
  - claim: "The releasing of an exit's cost basis weighs its figure the same way, finite and above nought"
    source: "`nexus/core/capital_controller/capital_controller.py` 754 into 755-756, then 758 into 759-760"
  - claim: "It weighs its strategy name the same way too, and trims it the same way"
    source: "`nexus/core/capital_controller/capital_controller.py` 762 into 763-764, then 766"
---
# What a strategy's budget is worked out from

A strategy's budget is a share of the pool, and with compounding it is that share plus whatever the strategy has made or lost.

## What is weighed first

The strategy's name, which must be text holding something other than spaces, and is then trimmed. Then the share, which must be a finite figure standing above nought and at or below a hundred.

So a share of exactly a hundred is allowed and a share of nought is refused: the budget can be the whole pool, and its base always stands above nought.

## The base

The pool multiplied by that share over a hundred. Without compounding, that is the whole answer and nothing else is read.

## What compounding adds

The realized figure, as it stands — sign and all. A strategy that has lost gets a smaller budget than its share, and one that has made gets a larger.

## The check that only one road makes

The realized figure is weighed for being finite only where compounding is asked for. The weighing stands after the answer the plain road gives.

So a figure that is not finite at all passes unnoticed on the plain road, and raises on the compounding one — the same figure, refused or ignored by which road reads it.

## The same weighing elsewhere

The releasing of an exit's cost basis weighs its figure the same way — finite, and above nought. It weighs its strategy name the same way too, and trims it the same way.

So the pattern is the module's rather than this routine's: a figure that must read as a number and stand above nought, and a name that must hold a character other than a space.

## Related

- [What becomes of money set aside](what-becomes-of-money-set-aside.md)
