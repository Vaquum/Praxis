---
row: P2-38
baseline: 49aa659
created: 2026-09-26 19:03 UTC
modified: 2026-09-27 13:46 UTC
evidence:
  - claim: "On the ordinary path an ending marks the command finished and drops it from the live and aborted sets"
    source: "`execution_manager.py` 10800-10804"
  - claim: "An ending that filled something and closes the position writes a close first"
    source: "`execution_manager.py` 10805-10815"
  - claim: "Then the outcome's own row is written and projected"
    source: "`execution_manager.py` 10817-10832"
  - claim: "Only then is the caller told"
    source: "`execution_manager.py` 10834"
  - claim: "A scheme ended at boot writes its row before marking the command finished, and writes no close"
    source: "`execution_manager.py` 2721-2773"
  - claim: "A caller that takes it on the first try is not tried again"
    source: "`execution_manager.py` 760-763"
  - claim: "Up to three tries are made"
    source: "`execution_manager.py` 760 with the count at 148"
  - claim: "A wait follows each failure but the last"
    source: "`execution_manager.py` 783 into the wait at 794, the base at 149"
  - claim: "The host being shut down is passed on rather than retried"
    source: "`execution_manager.py` 763-770"
  - claim: "When the tries run out it is logged and no further attempt is made"
    source: "`execution_manager.py` 771-782"
---
# How an outcome is delivered

An [outcome](what-an-outcome-is.md) is written down before it is handed over, and handing it over can fail.

## The ordinary order of things

On the path a live request takes, an ending marks the request finished and takes it off the lists of running and cancelled work.

Where that ending filled something and the position it leaves is closed by it, a close is written to [the record](the-event-spine.md) before anything else. Then the outcome's own row is written and projected. Only after all of that is the caller told.

That order belongs to that path. Work carried out as several orders, ended during a restart, writes its row first and marks the request finished afterwards, and writes no close at all.

## Handing it over

A caller that takes the outcome is not asked twice. One that fails is tried again, up to three tries in all, with a wait after each failure but the last — half a second, then one.

The host being shut down is not treated as a failed try. It is passed straight on, so stopping does not look like a caller that will not answer.

## When the tries run out

Three failures end it, with a line in the log.

What that means is narrower than it looks. The caller may have done most of its work and failed at the end of it. An exhausted attempt says only that the handing over failed to finish; what the caller had already taken in, it keeps.

The row already written is what remains, and it is [read again at the next start](how-an-undelivered-outcome-is-replayed.md).

[What that start offers again](who-a-restart-tells-again.md) is narrower than what failed.

## Related

- [Who a restart tells again](who-a-restart-tells-again.md)
- [How an undelivered outcome is replayed](how-an-undelivered-outcome-is-replayed.md)
- [Outcomes](what-an-outcome-is.md)
