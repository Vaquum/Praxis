---
row: P8-04
baseline: 49aa659
created: 2026-11-08 11:11 UTC
modified: 2026-11-08 11:11 UTC
evidence:
  - claim: "An alert gives back the severity it actually used"
    source: "`praxis/infrastructure/alert_sink.py` 53"
  - claim: "The telling that posts takes that answer rather than what it was handed"
    source: "`praxis/infrastructure/alert_sink.py` 58"
---
# The severity an alert gives back

Telling an alert hands back the severity it actually used, and the call that also posts reads that answer rather than its own argument.

## The answer

[An unknown severity is turned into a warning](alerts.md) before the line is written. What comes back from the telling is the severity after that turning.

So a caller that passes something unknown can learn what was really recorded, and one that never looks at the answer cannot.

## Why the posting reads it

The call that logs and then posts does the logging through the same telling, and takes its answer back. What it posts therefore carries the turned severity.

So the line written and the thing posted agree, and they agree because the second is taken from the first rather than worked out again.

## Related

- [Alerts](alerts.md)
