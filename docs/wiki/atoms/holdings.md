---
row: P2-16
baseline: 49aa659
created: 2026-09-26 05:47 UTC
modified: 2026-09-26 17:41 UTC
evidence:
  - claim: "Kept per trade and account, not per symbol"
    source: "`trading_state.py` 482, the record built at 489-497"
  - claim: "A fill on the same side adds what it delivered and reckons the average over the new total"
    source: "`trading_state.py` 500-505"
  - claim: "A fill on the other side takes that away"
    source: "`trading_state.py` 506-507"
  - claim: "A reducing fill reaching zero drops the record"
    source: "`trading_state.py` 517-522"
  - claim: "One going below zero is logged, set to zero, and dropped by that same test"
    source: "`trading_state.py` 508-522"
  - claim: "Closing the trade drops the record whatever it holds"
    source: "`trading_state.py` 571-572"
  - claim: "A trade can be closed with an amount still standing"
    source: "`execution_manager.py` 10891-10899, the close emitted at 10806-10816"
---
# Holdings

An account's **holdings** from one [trade](what-a-trade-is.md) are a side, an amount, and the average price paid to build it. There is one record per trade and account, so two trades on the same symbol are held apart.

A [fill](what-a-fill-is.md) on the same side as the record adds [what that fill delivered](the-commission-and-the-amount.md), and the average price is reckoned afresh over the new total. A fill on the other side takes the same figure away.

## When a record goes away

Three things remove one.

A reducing fill that brings the amount to zero drops it. One that would take the amount below zero is written to the log, set to zero, and then dropped by that same test — so overshooting and landing exactly both end with no record.

And closing the trade drops it whatever it holds. A trade can be closed with a small amount still standing, too small to sell on its own, and the record goes with the close rather than with a fill.

Only a reducing fill reaches the first two tests, and a record holding nothing still meets them: the next fill on the other side takes it below zero, where it is clamped and dropped like any other.

## Related

- [The commission and the amount](the-commission-and-the-amount.md)
- [What a fill is](what-a-fill-is.md)
