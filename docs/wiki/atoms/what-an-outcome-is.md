---
row: P2-18
baseline: 49aa659
created: 2026-09-26 20:21 UTC
modified: 2026-09-27 07:44 UTC
evidence:
  - claim: "An outcome is built with the names, a status, the amount filled and its average, a pair of slice figures, a reason and a time"
    source: "`execution_manager.py` 10784-10798"
  - claim: "Two statuses are not an ending and four are"
    source: "`enums.py` 171-176, the four gathered at `trade_outcome.py` 23-28 and tested at 171"
  - claim: "Its names must be real names and its time must carry a zone"
    source: "`trade_outcome.py` 111-116"
  - claim: "It is handed to a caller where one was given"
    source: "`execution_manager.py` 757-758, dispatched at 10834"
  - claim: "A restart looks only within the epoch it was told to run"
    source: "`launcher.py` 4521-4526"
  - claim: "How far along it is cannot be given where no target was"
    source: "`trade_outcome.py` 182-185"
---
# Outcomes

An **outcome** is what Praxis reports back about a [command](what-a-trade-is.md): which [account](what-an-account-is.md) and trade it belongs to, where it has got to, how much has filled and at what average, a pair of figures counting slices, why, and when that was true.


The same thing carries progress and completion. Two of its six states are not an ending — waiting, and part done — and four are: filled, cancelled, refused, and expired.

An outcome is refused as it is made unless its names are real names rather than empty ones, unless its time carries a zone, and unless [its figures agree](the-figures-an-outcome-carries.md).

[What those figures are worth](the-figures-an-outcome-reports.md) differs by which producer made the outcome.

## What becomes of it

An outcome is written down, then [handed to the caller](how-an-outcome-is-delivered.md) — where a caller was given at all; with none, the handing over is skipped.

Where the handing over does not finish, [the next start goes looking for it](how-an-undelivered-outcome-is-replayed.md). That looking is bounded by the epoch the host was told to run: an outcome from an earlier one falls outside it.

## Related

- [The figures an outcome reports](the-figures-an-outcome-reports.md)
- [The figures an outcome carries](the-figures-an-outcome-carries.md)
- [How an outcome is delivered](how-an-outcome-is-delivered.md)
