---
row: P9-02
baseline: 49aa659
created: 2026-11-10 03:30 UTC
modified: 2026-11-10 03:30 UTC
evidence:
  - claim: "The record on the Nexus side holds the same five figures to the same rules, written out separately"
    source: "`praxis/core/domain/health_snapshot.py` 43-74, against `nexus/core/health_evaluator.py` 40-58"
  - claim: "Nothing in either checkout compares the two"
    source: "`praxis/core/domain/health_snapshot.py` 43-74, which names the other nowhere, and `nexus/core/health_evaluator.py` 40-58, the same"
---
# The same record written twice

The report of how the venue is answering exists on both sides of the seam, as two separate pieces of code holding the same five figures to the same rules.

## What both hold

Four figures walked together for being finite numbers at or above nought, with a true-or-false refused. Two of the four held to a ceiling of one. The count of failures in a row held apart, as a whole number at or above nought.

Running both on the same figures gives the same answers: an infinity turned back, a share above one turned back, a true-or-false turned back wherever a number is wanted.

## What differs

The names of the fields the loops read, and how the lines are broken. In the count's check the two conditions stand in opposite order, which changes nothing — either order turns a true-or-false back, because the test is satisfied by whichever condition holds.

## What nothing does

Neither copy names the other, and nothing in either checkout compares them. A rule changed on one side and not the other would leave the two disagreeing about what a valid report is, and the disagreement would show only when a report accepted on one side was refused on the other.

This is the third place the wiki has found the two sides holding a copy each: [the named values](the-named-values-copied-from-the-other-side.md) the strategy layer writes its intent in, and [the arrangement that sets logging up](what-the-nexus-logging-adds.md), are the other two.

## Related

- [What the health report refuses](what-the-health-report-refuses.md)
- [What a health snapshot refuses](what-a-health-snapshot-refuses.md)
- [The named values copied from the other side](the-named-values-copied-from-the-other-side.md)
