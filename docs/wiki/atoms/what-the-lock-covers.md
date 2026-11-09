---
row: P13-02
baseline: 49aa659
created: 2026-11-08 14:17 UTC
modified: 2026-11-08 14:17 UTC
evidence:
  - claim: "The run of failures starts at nought and the lock is made as the tracker is"
    source: "`praxis/core/health_tracker.py` 46-47"
  - claim: "The two stores and the run of failures are changed under the lock"
    source: "`praxis/core/health_tracker.py` 74 into 75-80"
  - claim: "A report copies the two stores and the run under the lock, then lets it go"
    source: "`praxis/core/health_tracker.py` 102-105"
  - claim: "The two figures are worked out after the lock has gone"
    source: "`praxis/core/health_tracker.py` 107-108, reached after 105"
---
# What the lock covers

One lock guards the tracker's three pieces of state, and a report holds it only long enough to copy them.

## Where it begins

The run of failures starts at nought and the lock is made as the tracker is, so every later change to either has a lock to take.

## The writing

Recording a request takes the lock, appends the latency and the outcome, and moves the run of failures — to nought on a success, up by one on a failure.

So a reader cannot catch the stores and the run disagreeing about the same request.

## The reading

A report takes the lock, copies both stores into lists and the run into a figure, and lets the lock go. Only then are the slow-end latency and the failed share worked out.

The arithmetic therefore runs outside the lock, on copies taken inside it. That keeps the lock short while still giving figures drawn from one consistent set of samples: a request recorded while the arithmetic runs lands in the stores and not in the copies.

## Related

- [What recording a request refuses](what-recording-a-request-refuses.md)
- [Health](health.md)
