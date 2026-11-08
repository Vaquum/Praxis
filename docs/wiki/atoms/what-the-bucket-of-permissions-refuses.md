---
row: P9-03
baseline: 49aa659
created: 2026-11-10 03:30 UTC
modified: 2026-11-10 03:30 UTC
evidence:
  - claim: "A bucket of permissions refuses a rate at or below nought"
    source: "`praxis/infrastructure/token_bucket.py` 45-47"
  - claim: "It refuses a capacity at or below nought"
    source: "`praxis/infrastructure/token_bucket.py` 49-51"
  - claim: "It starts with as many tokens as its capacity"
    source: "`praxis/infrastructure/token_bucket.py` 55"
  - claim: "A take refills by the time elapsed times the rate, capped at the capacity, and notes the moment it refilled at"
    source: "`praxis/infrastructure/token_bucket.py` 75-80"
---
# What the bucket of permissions refuses

The bucket that paces calls to the venue refuses two things as it is made, and refills itself on every take.

## The two refusals

A rate at or below nought, and a capacity at or below nought. Each is a comparison, so neither asks the figure to be a whole number or a finite one.

## Where it starts

With as many tokens as its capacity. So the first calls after a bucket is made go through without waiting, as many of them as the capacity allows.

## How it refills

Every take reads the clock, adds the time elapsed since the last refill times the rate, and caps the total at the capacity. Then it notes the moment it refilled at, so the next take measures from there.

Capping at the capacity is what stops a long quiet spell buying an unlimited burst: a bucket of capacity two left alone for ten seconds at a rate of one is still a bucket of two.

## Related

- [The token taken before the waiting](the-token-taken-before-the-waiting.md)
- [When Praxis retries a venue call](when-praxis-retries-a-venue-call.md)
