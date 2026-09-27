---
row: P2-41
baseline: 49aa659
created: 2026-09-26 20:28 UTC
modified: 2026-09-27 07:08 UTC
evidence:
  - claim: "A piece is marked taken only where the caller succeeded and its changes were kept"
    source: "kept at `launcher.py` 4439-4441, both tested at 4464-4465"
  - claim: "Either kind of settling row keeps a piece out of the next plan"
    source: "`launcher.py` 1735-1736 gathering both, applied at 1773-1776"
  - claim: "A piece the caller refuses has a giving-up written instead"
    source: "the refusal at `launcher.py` 1824-1828, the row built and written at 3197-3208"
  - claim: "Waiting on that writing can time out, and the wait's failure is logged and passed over"
    source: "`launcher.py` 3209-3215"
  - claim: "A piece that raises has no giving-up written for it"
    source: "`launcher.py` 1817-1822"
  - claim: "Translation drops anything for a command it already considers ended, yielding nothing"
    source: "`outcome_translator.py` 156-164"
  - claim: "The plan is built only from what translation hands back"
    source: "`launcher.py` 1773-1777"
---
# Outcomes that never come back

A piece of a [replayed outcome](how-an-undelivered-outcome-is-replayed.md) stops being offered when the record says what became of it. Two rows can say that, and everything else leaves it owed.

## The two rows that settle it

A piece is marked taken where the caller succeeded and the changes it made were kept. Both are needed: a caller that succeeded while its changes went unkept is left owed, and offered again.

A piece the caller refuses has a giving-up written instead. That row settles it as surely as being taken does, and for the same reason — a later start reads both as done with.

## Everything else comes back

A piece that raises is logged, and no giving-up is written for it. Whatever the caller managed before it raised stands — the handler neither undoes that nor records it. The next start finds the piece owed and offers it once more, which is the point: a caller that was briefly unreachable gets another chance at every start.

Writing a giving-up can be slow. Praxis waits a short while for it, and gives up waiting rather than gives up writing: the failure to wait is logged, while the writing may yet finish. So a piece comes back only where no settling row lands in the end.

## The one that never arrives

Translation is what turns a recorded outcome into the pieces owed, and it drops anything belonging to a [command](what-a-trade-is.md) it already considers ended, handing back nothing.

The plan is built from what translation hands back, so that row contributes no piece at all. It is never offered, and no row is written about it. It is not owed, and it is not settled; it simply is not there.

## Related

- [How an undelivered outcome is replayed](how-an-undelivered-outcome-is-replayed.md)
