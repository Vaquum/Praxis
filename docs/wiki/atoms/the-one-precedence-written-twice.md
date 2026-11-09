---
row: P138-02
baseline: 49aa659
created: 2026-11-15 13:30 UTC
modified: 2026-11-15 13:30 UTC
evidence:
  - claim: "A linked pair whose legs are all done is reduced to one status by a fixed precedence: a fill, then a part fill, then an expiry, then a rejection, and a cancellation otherwise"
    source: "`execution_manager.py` 204 into 205, or 207 into 208, or 210 into 211, or 213 into 214, or 216"
  - claim: "The same five steps in the same order are written again where the venue's own answer to a fresh pair is read"
    source: "`binance_adapter.py` 985 into 986, or 987 into 988, or 989 into 990, or 991 into 992, or 993 into 994"
  - claim: "The adapter's reaches that precedence only where the pair reports itself all done, and sends any other list status through a mapping that refuses an unknown one"
    source: "`binance_adapter.py` 982, then 983, against 995 into 996-997, then 998 into 999-1000"
  - claim: "The manager's has no such gate, being reached from the asking that rescues a pair's legs one at a time"
    source: "`execution_manager.py` 5690, then 5692"
  - claim: "A leg whose asking fails answers that the whole pair is live, so the precedence is reached only where every leg answered"
    source: "`execution_manager.py` 5688, against 5690"
  - claim: "The adapter weighs the venue's own words and the manager weighs statuses already read"
    source: "`binance_adapter.py` 984, against `execution_manager.py` 5690"
---
# The one precedence written twice

A linked pair of protective orders has two legs and one status, and the rule reducing the two to the one is written in two places.

## The rule

A fill on either leg makes the pair filled. Failing that, a part fill makes it part filled. Then an expiry, then a rejection, and [a cancellation](how-a-trade-is-cancelled.md) where none of the four applies.

Five steps, in that order, in both places.

## Where each is reached from

The adapter's is reached when the venue answers a freshly placed pair, and only where that answer reports the pair all done. Any other list status goes through a mapping instead, which refuses a status it does not know.

The manager's is reached from the asking that rescues a pair by querying each leg on its own. It has no gate at all: whatever statuses the legs gave are reduced.

## What each is weighing

The adapter weighs the venue's own words, gathered as a set. The manager weighs statuses already read into Praxis's own terms, gathered as a list in leg order.

So the two agree on the rule and differ on what the rule is applied to, and on whether anything checks first that the pair is finished.

## What a failed asking does instead

A leg whose asking fails answers that the whole pair is live, before the precedence is reached. So the manager's rule runs only where every leg answered — and a single unreachable leg keeps the pair open rather than reducing it.

## Related

- [How a venue answer becomes a record](how-a-venue-answer-becomes-a-record.md)
- [Protection](protection.md)
- [Part-shown orders](part-shown-orders.md)
