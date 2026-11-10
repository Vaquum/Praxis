---
row: P9-04
baseline: 49aa659
created: 2026-11-08 13:35 UTC
modified: 2026-11-08 13:35 UTC
evidence:
  - claim: "The wait is worked out where fewer than one token is left, and is nought otherwise"
    source: "`praxis/infrastructure/token_bucket.py` 82"
  - claim: "The token is taken whether one was there or not, so the count can fall below nought"
    source: "`praxis/infrastructure/token_bucket.py` 83"
  - claim: "The waiting happens after the lock is let go"
    source: "`praxis/infrastructure/token_bucket.py` 85-87, the lock opened at 74"
  - claim: "A wait cut short part way puts one token back, capped at the capacity, and raises on"
    source: "`praxis/infrastructure/token_bucket.py` 88-94, then 95"
---
# The token taken before the waiting

A take works out how long it must wait, subtracts its token, and only then lets the lock go and waits.

## The order

The wait is worked out first: where fewer than one token is left, it is what the rate needs to make up the difference, and otherwise nought. Then the token is subtracted — whether one was there or not.

So the count can fall below nought, and the further below it falls the longer the next take waits. A bucket of capacity two taken from four times with no time passing holds minus two, and the third and fourth takes wait one second and two.

## Why the lock can go early

Because the token is already taken, nothing another take could do would change what this one owes. The lock is let go before the waiting, so a take that must wait does not hold the next one out of the arithmetic.

## What a wait cut short puts back

A wait cut short part way adds one token back, capped at the capacity, and raises on.

Without that, such a take would leave the count a token lower for good, and every later take would wait longer for a token nobody spent.

## Related

- [What the bucket of permissions refuses](what-the-bucket-of-permissions-refuses.md)
- [When Praxis retries a venue call](when-praxis-retries-a-venue-call.md)
