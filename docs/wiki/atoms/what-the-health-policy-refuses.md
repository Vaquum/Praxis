---
row: N15-02
baseline: 49aa659
created: 2026-11-08 10:13 UTC
modified: 2026-11-08 14:48 UTC
evidence:
  - claim: "Ten thresholds are walked by name and each refused unless it is a finite number at or above nought, with a true-or-false refused outright"
    source: "`nexus/core/health_evaluator.py` 98-103 into 105-107"
  - claim: "Three more are walked for being whole numbers at or above nought, on the same terms"
    source: "`nexus/core/health_evaluator.py` 109-111 into 112-113"
  - claim: "Four orderings are each checked as one chain of two comparisons"
    source: "`nexus/core/health_evaluator.py` 115-117, or 119-121, or 123-125, or 127-129"
  - claim: "Those orderings are the only checks the policy makes that put two of its own fields side by side"
    source: "`nexus/core/health_evaluator.py` 98-138, which compares two of its fields at 115, 119, 123 and 127 and nowhere else"
  - claim: "A weigher built with no policy of its own takes the built-in thresholds"
    source: "`nexus/core/health_evaluator.py` 153, the defaults at 81-93"
  - claim: "Six of the thresholds are held to a ceiling of one by a walk that runs after the orderings"
    source: "`nexus/core/health_evaluator.py` 131-134 into 136-138"
---
# What the health policy refuses

The policy a snapshot is weighed against carries thirteen thresholds, and is refused for failing any one of a fixed list of checks on them.

A policy is optional. A weigher built without one takes the built-in thresholds, which are the ones these checks guard.

## The two walks over single fields

Ten are walked by name and each refused unless it is a finite number at or above nought. Three more — the counts of failures in a row — are walked for being whole numbers at or above nought. A true-or-false is refused outright in both walks.

## The four orderings

Each measure's three thresholds must rise, or at least not fall: the alerting one no higher than the acting one, and that no higher than the halting one. Each ordering is one chain of two comparisons, so a middle threshold below the first or above the last is refused by the same line.

Three thresholds all equal are let by: the chain asks that none exceeds the next, not that each exceeds it.

These are the only checks the policy makes that put two of its own fields side by side.

## The ceiling that comes last

Six of the thresholds — the shares — are refused above one by a walk that runs after the orderings. So a set of shares that rise in order and all stand above one passes every ordering and is turned back by that walk.

## Related

- [What a health snapshot refuses](what-a-health-snapshot-refuses.md)
- [How the mode is settled](how-the-mode-is-settled.md)
- [The thresholds nothing weighs against](the-thresholds-nothing-weighs-against.md)
