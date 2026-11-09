---
row: N78-02
baseline: 49aa659
created: 2026-11-13 11:30 UTC
modified: 2026-11-13 11:30 UTC
evidence:
  - claim: "An acceptance marks money as moved only for an entry, the money call standing past the answer every other order takes"
    source: "`nexus/infrastructure/praxis_connector/outcome_processor.py` 206 into 209, reached only past 191, the call at 197"
  - claim: "An acceptance that failed its money call carries only the kind and a reason"
    source: "`nexus/infrastructure/praxis_connector/outcome_processor.py` 199-200 into 201-203"
  - claim: "A fill's answer carries a mark tracked through the pass, set false before any work and turned true once the money call came back"
    source: "`nexus/infrastructure/praxis_connector/outcome_processor.py` 222, then 239, or 254, read at 293"
  - claim: "A rejection and a cancellation each mark money with whether their own money call succeeded"
    source: "`nexus/infrastructure/praxis_connector/outcome_processor.py` 305 read at 319-323, and 331 read at 351-355"
  - claim: "Either answers that it worked while marking money unmoved, where the failure was passed over for being an exit"
    source: "`nexus/infrastructure/praxis_connector/outcome_processor.py` 323, reached only where 312 did not answer, and 355 where 344 did not"
  - claim: "Neither consults the position itself for its position mark, taking only what clearing a pending sale reported"
    source: "`nexus/infrastructure/praxis_connector/outcome_processor.py` 307 into 310, or 333 into 342"
---
# What each outcome's answer records

An answer from the processor carries four things: whether it worked, which kind of outcome it was, whether a position changed, and whether money moved. [The last two stand clear](what-writes-the-name-a-success-records.md) unless the handler passes something, and what each handler passes differs.

## An acceptance

Marks money as moved — for an entry. The money call itself stands past the answer that [every other order's acceptance takes](what-writes-the-name-a-success-records.md), so an exit's acceptance answers with both marks clear, the money call behind it.

An acceptance whose money call failed carries only the kind and a reason.

## A fill

Carries a mark tracked through the pass: set false before any work, turned true on whichever road its money call came back on, and read into the answer at the end.

## A rejection and [a cancellation](how-a-trade-is-cancelled.md)

Each marks money with whether its own money call succeeded, rather than with having made the call.

So either can answer that it worked while marking that money did not move — which is what happens to an exit, [whose failed money call is passed over](what-an-entry-outcome-changes.md) where an entry's would end the pass. The answer carries the failure in the mark instead of in the verdict.

A caller reading the verdict alone cannot tell those apart. A caller reading the mark can.

## What a position mark means

Neither handler consults the position itself. The mark is whatever clearing a pending sale reported, so a rejection or cancellation of an entry marks no position, having nothing to clear.

## Related

- [What an entry outcome changes](what-an-entry-outcome-changes.md)
- [What writes the name a success records](what-writes-the-name-a-success-records.md)
- [What a pending sale does to the dust](what-a-pending-sale-does-to-the-dust.md)
