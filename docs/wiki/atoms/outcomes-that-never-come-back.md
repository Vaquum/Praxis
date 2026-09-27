---
row: P2-41
baseline: 49aa659
created: 2026-09-26 20:28 UTC
modified: 2026-09-27 09:35 UTC
evidence:
  - claim: "A report is marked received only where the receiver took it and its changes were saved"
    source: "kept at `launcher.py` 4439-4441, both tested at 4464-4465"
  - claim: "Either kind of closing record keeps a report off the next list"
    source: "`launcher.py` 1735-1736 gathering both, applied at 1773-1776"
  - claim: "A report the receiver rejects has a stopped-trying record written instead"
    source: "the refusal at `launcher.py` 1824-1828, the row built and written at 3197-3208"
  - claim: "Waiting on that writing can time out, and the failure to wait is logged and passed over"
    source: "`launcher.py` 3209-3215"
  - claim: "A report whose sending throws has no stopped-trying record written for it"
    source: "`launcher.py` 1817-1822"
  - claim: "The turning drops anything for a command it already treats as ended, returning nothing"
    source: "`outcome_translator.py` 156-164"
  - claim: "The list is built only from what the turning returns"
    source: "`launcher.py` 1773-1777"
---
# Outcomes that never come back

A [resent report](how-an-undelivered-outcome-is-replayed.md) stops being sent again once a record says what became of it. Two records can say that, and anything else leaves it waiting.

## The two records that close it

A report is marked received where the receiver took it and the changes it made were saved. Both are needed: a receiver that took a report while its changes went unsaved leaves that report waiting, and it is sent again.

A report the receiver rejects has a record written saying Praxis stopped trying. That closes it as surely as being received does, and for the same reason — a later startup reads both as finished with.

## Everything else comes back

A report whose sending throws an error is logged, and no record is written about it. Whatever the receiver managed before the error stands; the error handling neither undoes it nor notes it. The next startup finds the report waiting and sends it once more, which is the point: a receiver that was briefly unreachable gets another chance every time Praxis starts.

Writing the stopped-trying record can be slow. Praxis waits a short while, then stops waiting — but the writing may still finish. So a report comes back only where no closing record lands in the end.

## The one that never arrives

Turning an outcome into reports drops anything belonging to a [request](what-a-trade-is.md) it already treats as ended, returning no report at all.

The list is built from what comes back from that turning, so such an outcome puts nothing on it. It is never sent, and no record is written about it. It is neither waiting nor closed; it is simply absent.

## Related

- [How an undelivered outcome is replayed](how-an-undelivered-outcome-is-replayed.md)
