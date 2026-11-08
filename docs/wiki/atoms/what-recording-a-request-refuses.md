---
row: P13-01
baseline: 49aa659
created: 2026-11-10 11:30 UTC
modified: 2026-11-10 20:00 UTC
evidence:
  - claim: "Recording a request refuses a latency unless it is a finite number at or above nought, with a true-or-false refused outright"
    source: "`praxis/core/health_tracker.py` 61-68"
  - claim: "It refuses a success flag that is not a true-or-false, a whole number of one turned back as well"
    source: "`praxis/core/health_tracker.py` 70-72"
---
# What recording a request refuses

Nothing reaches the tracker's stores without passing two checks, and both are stricter than the records around them.

## The latency

A finite number at or above nought. A true-or-false is refused outright, though such a thing counts as a number.

Asking for finiteness turns back an infinity and a figure that is not a number. Five records elsewhere on these two sides refuse a figure by comparing it with nought instead, and where the figure is an ordinary number such a comparison turns back neither.

## The flag

A true-or-false, and nothing standing in for one. A whole number of one is refused, and so is text.

That is unusual too: [the record saying how one report was handled](what-a-record-of-processing-refuses.md) turns on a flag it never asks the type of, so text there is read for truth alone. Here the type is asked first.

## Related

- [What the lock covers](what-the-lock-covers.md)
- [Health](health.md)
- [What the health report refuses](what-the-health-report-refuses.md)
