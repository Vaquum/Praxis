---
row: P102-03
baseline: 49aa659
created: 2026-11-14 04:30 UTC
modified: 2026-11-14 04:30 UTC
evidence:
  - claim: "The command the order carries is read, and the manager asked which trade it belongs to"
    source: "`praxis/trading.py` 1610, then 1611"
  - claim: "Where the manager can name no trade, the backfilled trade is dropped with nothing said"
    source: "`praxis/trading.py` 1612 into 1613"
  - claim: "The socket road drops the same absence with a warning instead"
    source: "`praxis/trading.py` 1781 into 1782-1786"
  - claim: "Otherwise a fill is built carrying the venue trade's own moment, names, side, amount, price and fee"
    source: "`praxis/trading.py` 1615, through 1617-1629"
  - claim: "It is then admitted to the manager marked as coming from a recovery"
    source: "`praxis/trading.py` 1632-1633"
---
# What a backfilled trade becomes

A trade the backfill found becomes a fill admitted to the manager, marked as having come from a recovery rather than from the venue's socket.

## What is asked first

The command the order carries is read, and the manager asked which trade it belongs to.

## Where it stops

Where the manager can name no trade, the backfilled trade is dropped with nothing said. [The socket road drops the same absence with a warning](what-a-report-becomes.md).

So the identical condition is noisy on one road and silent on the other. A reader watching the log for lost fills sees the socket's and never the backfill's, and the backfill is the road more likely to meet it — it asks about trades from before the process started.

## What is built

A fill carrying the venue trade's own moment, its names, its side, its amount, its price and its fee. Every field comes from the venue's record rather than from the local order, except the command and the trade it belongs to.

## How it enters

Admitted to the manager marked as coming from a recovery. So the manager can tell a fill the backfill found from one the socket delivered, even though the two are built to the same shape.

## Related

- [What a backfill records as confirmed](what-a-backfill-records-as-confirmed.md)
- [What a report becomes](what-a-report-becomes.md)
