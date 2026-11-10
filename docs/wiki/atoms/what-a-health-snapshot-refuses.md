---
row: N15-01
baseline: 49aa659
created: 2026-11-08 10:13 UTC
modified: 2026-11-08 10:13 UTC
evidence:
  - claim: "Four of a health snapshot's figures are walked by name and each refused unless it is a finite number at or above nought, with a true-or-false refused outright"
    source: "`nexus/core/health_evaluator.py` 40-42 over the four names, into 43-44"
  - claim: "Two of those four are then held to a ceiling of one by a second walk over the pair"
    source: "`nexus/core/health_evaluator.py` 46-48 into 49-50"
  - claim: "The count of failures in a row is reached by neither walk, and is refused unless it is a whole number, with a true-or-false refused outright"
    source: "`nexus/core/health_evaluator.py` 52-54, the walks at 40 and 46 naming it nowhere"
  - claim: "That count is refused again where it stands below nought"
    source: "`nexus/core/health_evaluator.py` 56-58"
---
# What a health snapshot refuses

A snapshot of how the trading side is faring carries five figures, and is refused for failing any one of a fixed list of checks on them.

## The four walked together

How long requests are taking at the slow end, the share that failed, how much of the venue's allowance is in use, and how far the clock has drifted. One loop takes the four by name and refuses each unless it is a finite number at or above nought. A true-or-false is refused outright, though such a thing counts as a number.

Asking for finiteness here turns back an infinity and a figure that is not a number alike, which is more than a comparison with nought would do.

## The ceiling on the two shares

A second walk takes the share that failed and the share of the allowance in use, and refuses either above one. A share standing exactly at one is let by.

The other two of the four carry no ceiling, so a drift of any finite size is kept.

## The count held apart

The count of failures in a row is reached by neither walk. It is refused unless it is a whole number — a true-or-false again refused outright — and refused again where it stands below nought.

## Related

- [What the health policy refuses](what-the-health-policy-refuses.md)
- [How the mode is settled](how-the-mode-is-settled.md)
- [Health](health.md)
