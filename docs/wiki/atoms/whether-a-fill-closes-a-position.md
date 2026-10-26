---
row: N5-03
baseline: 49aa659
created: 2026-10-25 11:20 UTC
modified: 2026-10-26 11:20 UTC
evidence:
  - claim: "The question is asked where an ending has arrived and something filled against it, and answered yes or no"
    source: "`praxis/core/execution_manager.py` 10801-10808 into 10878-10899"
  - claim: "Where the book holds no position for that trade, the answer is whether the count of fills that have emptied one stands above nought"
    source: "`praxis/core/execution_manager.py` 10878-10881 into 10887-10889, the count kept at `praxis/core/trading_state.py` 517-522 and read at 561-564"
  - claim: "Where it does hold one, a fill on that position's own side answers no"
    source: "`praxis/core/execution_manager.py` 10891-10892"
  - claim: "A fill on the position's own side adds to its size, and one on the other side takes from it"
    source: "`praxis/core/trading_state.py` 500-507 into 516"
  - claim: "A fill on the other side with the venue's filters not to hand answers yes"
    source: "`praxis/core/execution_manager.py` 10894-10897"
  - claim: "Otherwise the answer is whether what the position has left falls below the step the venue keeps its sizes on"
    source: "`praxis/core/execution_manager.py` 10898-10899, the step taken from the venue at `praxis/infrastructure/binance_adapter.py` 2220-2225"
  - claim: "A yes is what lets the close be written to the record, and the record of it takes the position out of the book and reads the count down"
    source: "`praxis/core/execution_manager.py` 10806-10816 into `praxis/core/trading_state.py` 570-579"
---
# Whether a fill closes a position

An ending with something filled against it is asked whether that fill closed the trade's position, and the answer decides whether a close is written down.

## No position to look at

Where the book holds no position for that trade, the answer is [whether a fill has already emptied one](what-the-host-counts-when-a-fill-empties-a-position.md) — a trade that has just sold out of its last holding and one that never held anything look alike from the book alone.

## A position still there

A fill on the position's own side answers no — it is adding to the position rather than reducing it.

A fill on the other side is reducing the position, and then the question is how much is left. With the venue's filters not to hand there is no size to weigh against, and the answer is yes. With them to hand, the answer is whether what is left falls below the step the venue keeps its sizes on — a remainder smaller than the step is treated as closed.

## What a yes does

A yes is what lets the close be written to the record — and that record, once read, takes the position out of the book and reads [the count](what-the-host-counts-when-a-fill-empties-a-position.md) down.

## Related

- [What the host counts when a fill empties a position](what-the-host-counts-when-a-fill-empties-a-position.md)
- [The sizes a venue trades in](the-sizes-a-venue-trades-in.md)

---

Created 2026-10-25 11:20 UTC · Last modified 2026-10-25 11:20 UTC
