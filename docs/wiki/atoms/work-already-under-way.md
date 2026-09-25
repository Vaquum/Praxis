---
row: P1-09
baseline: 49aa659
created: 2026-09-23 18:56 UTC
modified: 2026-09-25 18:14 UTC
evidence:
  - claim: "The cancellation retry runs before the point a held or failed account leaves"
    source: "`execution_manager.py` 3960, ahead of the leaving point at 3969-3971"
  - claim: "It needs the work eligible: draining, no change in progress, children still working"
    source: "`execution_manager.py` 7051-7057"
  - claim: "A flagged retry drives it outright, otherwise the retry time must have come"
    source: "`execution_manager.py` 7089-7090, otherwise 7092-7094, read at 7061-7062"
  - claim: "Slice work and waiting protection come after that leaving point"
    source: "`execution_manager.py` 3973-3974"
  - claim: "Each fed-out run is wound up, advanced, or examined for completion"
    source: "wound up at `execution_manager.py` 5817-5824, or after the due test at 5831-5837 either advanced at 5838-5839 or examined at 5840-5841"
  - claim: "Winding up needs four things: not already winding up, no change in progress, a deadline set, and the time past it"
    source: "`execution_manager.py` 5817-5822"
  - claim: "A change in progress is only ever set on a ladder"
    source: "`execution_manager.py` 1464, 8942, 9014, 9253"
  - claim: "Winding up cancels live children and the run stays on the books until they settle"
    source: "`execution_manager.py` 8375-8383, held open at 6355-6356 while a child remains, a failed cancel leaving it there at either 6459-6460 or 6461-6468"
  - claim: "A cancel reply whose status or fields cannot be read stops the account when it happens on the early drain or on winding up"
    source: "raised at `binance_adapter.py` 897, or reading the reply at 1690-1691, leaving the try at `execution_manager.py` 6454-6458 without either handler, reaching 4025-4026 from 3960 or 8382"
  - claim: "The same failure inside the sweep is caught and the account carries on"
    source: "`execution_manager.py` 7303-7308"
  - claim: "A cancel whose body will not parse is caught and the run carries on"
    source: "wrapped at `binance_adapter.py` 660-662, caught instead at `execution_manager.py` 6461-6468"
  - claim: "Advancing needs the run open and the slice due"
    source: "`execution_manager.py` 5831-5835"
  - claim: "A slice that cannot be placed freezes the run and reports a partial instead"
    source: "`execution_manager.py` 5910-5916, the freeze set at 8294-8296"
  - claim: "A slice that fails outright ends the run and drops it"
    source: "`execution_manager.py` 5866-5883"
  - claim: "Protection is placed once the entry has settled with a fill"
    source: "settled at `execution_manager.py` 4741-4743, a fill required at 4748-4749, placed at 4751-4763 unless already done at 4739-4740"
  - claim: "Wrong-side legs, an empty rescue and a venue error hand over to repair"
    source: "either `execution_manager.py` 4947-4965, 4983-4997 or 5000-5015, handing over at 4958, 4990 and 5008"
  - claim: "A status or field that cannot be read escapes those handlers and stops the account when the waiting call places it"
    source: "raised at `binance_adapter.py` 999-1000 or 969-982, unhandled in `_place_bracket_protection`, reaching `execution_manager.py` 4025-4026 from 4753 called at 3974"
  - claim: "The same failure from a venue event or a settling entry is logged and swallowed instead"
    source: "`execution_manager.py` 3868-3874 from 4715, or 4012-4019 from 4635"
  - claim: "A body that will not parse at all is handled instead, being wrapped and looked up"
    source: "`binance_adapter.py` 660-662 wrapped at 1637-1643, looked up at `execution_manager.py` 4979-4982, then either handed to repair at 4983-4997 or adopted at 4999"
  - claim: "A settled entry that filled nothing is dropped from the list"
    source: "`execution_manager.py` 4746-4749"
  - claim: "With nothing held the record is put back and tried again"
    source: "`execution_manager.py` 4887-4904, returning rather than reaching the flag set at 4906"
  - claim: "The sweep runs seven repair jobs in order"
    source: "`execution_manager.py` 7290-7301, reached from 3976-3978"
  - claim: "Its first job repeats the drain with the timing test dropped"
    source: "`execution_manager.py` 6968, which omits the test read at 7061"
---
# Work already under way

Between emptying [the priority line](the-priority-line.md) and taking a new piece of [submitted work](how-an-order-is-placed.md), [the worker](how-waiting-work-is-drained.md) carries on with what it has already started. Each kind has its own conditions, and a pass may satisfy none of them.

## What it carries on

A [cancellation](how-a-trade-is-cancelled.md) under way is retried, where the work is eligible and either a retry is flagged or its time has come. This runs early, before a held or failed account leaves the pass.

The rest come after that point, so a held or failed account never reaches them.

Every run being fed out is looked at. It may be wound up, when it is not already winding up, no change is in progress, and its deadline has passed; that cancels its live children, and the run stays on the books until they settle. A cancel whose reply has [a status or field Praxis cannot read](a-reply-that-cannot-be-read.md) stops the account instead. It may have its next slice released, when the run is open and that slice is due; a slice that cannot be placed freezes the run, and one that fails outright ends it. Otherwise it is examined for completion.

Protection waiting is placed once the opening order has settled with something filled. Several failures hand it to repair; a reply with a status or field Praxis cannot read is not among them, and stops the account. A settled entry that filled nothing is dropped instead. Where something filled but nothing is held under the trade, the record is put back for a later pass.

## The sweep

When one has been asked for, a sweep of seven repair jobs runs last. The first repeats the cancellation retry with its timing test dropped, so work the earlier step passed over can still be driven that pass.

## Related

- [The account worker](how-waiting-work-is-drained.md)
- [The priority line](the-priority-line.md)
