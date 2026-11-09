---
row: P110-02
baseline: 49aa659
created: 2026-11-09 08:31 UTC
modified: 2026-11-09 08:31 UTC
evidence:
  - claim: "A rate limiting is retried only where attempts remain and the status was the one that means too many"
    source: "`binance_adapter.py` 605 into 606"
  - claim: "A rate limiting that will not be retried is recorded as unhealthy and raised on"
    source: "`binance_adapter.py` 607, then 608"
  - claim: "The wait before a retry is the venue's own where it gave one, held at nought at the least"
    source: "`binance_adapter.py` 609"
  - claim: "Where the venue gave none, the wait is drawn at random from a span that doubles with each attempt"
    source: "`binance_adapter.py` 609, the span widening by the attempt"
  - claim: "A not-found is recorded as healthy before it is raised on"
    source: "`binance_adapter.py` 655, then 656"
  - claim: "Every other venue failure is recorded as unhealthy before it is raised on"
    source: "`binance_adapter.py` 657 into 658, then 659"
  - claim: "A transport failure, a timing out or an unreadable answer is turned into a passing failure and kept rather than raised"
    source: "`binance_adapter.py` 660 into 661-662"
---
# Which failures a retry counts as healthy

The retry records each failure against the venue's health, and one kind of failure is recorded as a success.

## The one counted healthy

A not-found. It is recorded as healthy before being raised on, because the venue answered correctly — the thing asked about simply was not there.

So an adapter asking after an order the venue has forgotten does not make the venue look unwell, and a run full of not-founds leaves the health untouched.

## Everything else

Every other venue failure is recorded as unhealthy before it is raised on. A rate limiting that will not be retried is recorded unhealthy too.

## What is retried

A rate limiting, and only where attempts remain and the status was the one that means too many. So the other two statuses that produce a rate limiting are raised at once rather than retried.

## The wait before a retry

The venue's own where it gave one, held at nought at the least. Where the venue gave none, the wait is drawn at random from a span that doubles with each attempt.

So a venue that says how long to wait is obeyed, and one that says nothing is backed off from with a spread rather than a fixed delay — which keeps several callers from returning together.

## The failures kept rather than raised

A transport failure, a timing out, or an unreadable answer. Each is turned into a passing failure and kept, for the loop to decide about.

## Related

- [How a venue failure is sorted](how-a-venue-failure-is-sorted.md)
