---
row: P102-01
baseline: 49aa659
created: 2026-11-14 04:30 UTC
modified: 2026-11-14 04:30 UTC
evidence:
  - claim: "An account the manager holds no state for is answered as complete without anything being asked of the venue"
    source: "`praxis/trading.py` 1524 into 1525-1526"
  - claim: "The symbols asked about are the account's active ones together with the ones a bootstrap filters on"
    source: "`praxis/trading.py` 1529-1532"
  - claim: "They are walked in sorted order, so the asking is in the same order every time"
    source: "`praxis/trading.py` 1533"
  - claim: "Each symbol's asking begins from the cursor the spine holds for it"
    source: "`praxis/trading.py` 1534, handed on at 1543"
  - claim: "Where the spine holds no cursor, a window back from the clock stands in instead"
    source: "`praxis/trading.py` 1535-1538, handed on at 1544"
  - claim: "A symbol whose pages ran out unfinished turns the whole answer to incomplete, and the walk goes on to the next symbol"
    source: "`praxis/trading.py` 1546 into 1547, against 1528"
---
# What a backfill asks the venue for

A backfill asks the venue for the trades it may have missed, symbol by symbol, and reports whether it got all of them.

## The account it does nothing for

One the manager holds no state for is answered as complete, without anything being asked of the venue. So an account that was never registered reports a finished backfill rather than a failed one.

## Which symbols

The account's active ones, together with the ones a bootstrap filters on. They are walked in sorted order, so the asking is in the same order every time.

The union means a symbol the account is no longer active in is still asked about, as long as a bootstrap names it.

## Where each asking begins

From the cursor the spine holds for that symbol. Where the spine holds none, a window back from the clock stands in instead.

So a symbol asked about for the first time looks back a fixed distance, and every later asking continues from where the last one confirmed.

## What makes the answer incomplete

A symbol whose pages ran out unfinished. It turns the whole answer to incomplete, and the walk goes on to the next symbol regardless — so one truncated symbol does not stop the others being asked, and the caller learns only that something was truncated.

## Related

- [What a backfill records as confirmed](what-a-backfill-records-as-confirmed.md)
