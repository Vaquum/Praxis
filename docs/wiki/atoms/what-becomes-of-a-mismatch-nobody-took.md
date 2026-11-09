---
row: P103-02
baseline: 49aa659
created: 2026-11-14 05:00 UTC
modified: 2026-11-14 05:00 UTC
evidence:
  - claim: "A mismatch is named for the account, the asset and the shortfall itself"
    source: "`praxis/trading.py` 1274"
  - claim: "It is written to the spine before anyone is told, and reported as a warning"
    source: "`praxis/trading.py` 1280, ahead of 1286"
  - claim: "Delivery hands it to the callback inside a guard whose catch names any failure"
    source: "`praxis/trading.py` 1325-1326 into 1327"
  - claim: "A failed delivery answers that it failed rather than raising"
    source: "`praxis/trading.py` 1333, against 1335"
  - claim: "A delivered mismatch has its shortfall remembered as seen and any waiting copy cleared"
    source: "`praxis/trading.py` 1286 into 1287, then 1288"
  - claim: "An undelivered one is kept against the account and asset instead"
    source: "`praxis/trading.py` 1290"
  - claim: "Those kept are tried again at the start of the next comparison"
    source: "`praxis/trading.py` 1251"
---
# What becomes of a mismatch nobody took

A mismatch is recorded whether or not anyone accepts it, and what happens next turns on whether the callback raised.

## Its name

The account, the asset and the shortfall itself. So two different shortfalls on one asset are two different mismatches, and the same shortfall reported twice would carry the same name.

## The order of the writing

It is written to the spine before anyone is told, and reported as a warning. So the record exists even where delivery fails, and a mismatch in the spine is not evidence that anybody heard about it.

## The delivery

The callback is handed the mismatch inside a guard whose catch names any failure. A failed delivery answers that it failed rather than raising, so the comparison carries on to the next asset and the loop above it never sees the failure.

## The two memories

A delivered mismatch has its shortfall remembered as seen, and any waiting copy cleared. An undelivered one is kept against the account and asset instead.

The two are complementary: one records what has been reported, the other what still owes a report.

## The retry

Those kept are tried again at the start of the next comparison, before any asset is weighed. So a listener that was down recovers the backlog on the next pass rather than waiting for the shortfall to change.

## Related

- [What a balance comparison weighs](what-a-balance-comparison-weighs.md)
