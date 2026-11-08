---
row: P9-01
baseline: 49aa659
created: 2026-11-10 03:30 UTC
modified: 2026-11-10 03:30 UTC
evidence:
  - claim: "Four of the report's figures are walked by name and each refused unless it is a finite number at or above nought, with a true-or-false refused outright"
    source: "`praxis/core/domain/health_snapshot.py` 43-48 into 50-57"
  - claim: "Two of those four are then held to a ceiling of one by a second walk"
    source: "`praxis/core/domain/health_snapshot.py` 59-61 into 62-63"
  - claim: "The count of failures in a row is reached by neither walk, and is refused unless it is a whole number, a true-or-false refused outright"
    source: "`praxis/core/domain/health_snapshot.py` 65-68 into 69-70, the walks at 43 and 59 naming it nowhere"
  - claim: "That count is refused again where it stands below nought"
    source: "`praxis/core/domain/health_snapshot.py` 72-74"
---
# What the health report refuses

The report Praxis keeps of how the venue is answering carries five figures, and is refused for failing any one of a fixed list of checks on them.

## The four walked together

How long requests are taking at the slow end, the share that failed, how much of the venue's allowance is in use, and how far the clock has drifted. One loop takes the four by name and refuses each unless it is a finite number at or above nought. A true-or-false is refused outright.

Asking for finiteness turns back an infinity as well as a figure that is not a number, which a comparison with nought alone would not do.

## The ceiling on the two shares

A second walk takes the share that failed and the share of the allowance in use, and refuses either above one. A share standing exactly at one is let by, and the other two of the four carry no ceiling.

## The count held apart

The count of failures in a row is reached by neither walk. It is refused unless it is a whole number — a true-or-false again refused — and refused again where it stands below nought.

## Related

- [The same record written twice](the-same-record-written-twice.md)
- [Health](health.md)
- [What a health snapshot refuses](what-a-health-snapshot-refuses.md)
