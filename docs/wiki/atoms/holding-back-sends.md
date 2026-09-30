---
row: P3-18
baseline: 49aa659
created: 2026-09-30 10:22 UTC
modified: 2026-09-30 17:25 UTC
evidence:
  - claim: "A store of permits refills steadily and is capped"
    source: "`token_bucket.py` 76-79"
  - claim: "Each call takes one permit, which may leave the store below nothing"
    source: "`token_bucket.py` 83"
  - claim: "The wait is worked out once, counting what others already took"
    source: "`token_bucket.py` 82, slept at 87"
  - claim: "A call given up on hands its permit back"
    source: "`token_bucket.py` 88-95"
  - claim: "The waiting happens after the store is released"
    source: "`token_bucket.py` 85-87, past the holding at 74"
  - claim: "Three kinds of call to the exchange take a permit"
    source: "`binance_adapter.py` 588, 2173 and 2263"
  - claim: "Asking the exchange the time takes none, and reads no allowance"
    source: "`binance_adapter.py` 2353-2364"
  - claim: "The allowance used is read from the answers that carry it"
    source: "`binance_adapter.py` 2425 into 2428-2433"
  - claim: "A limit of six thousand stands until the venue says otherwise"
    source: "`binance_adapter.py` 303 with the figure at 98"
  - claim: "An answer carrying no limits leaves the one already known"
    source: "`binance_adapter.py` 2470-2474"
  - claim: "Where the limit is nothing or less, nought is reported rather than a share"
    source: "`binance_adapter.py` 2327-2328, assembled at 2394-2403"
  - claim: "The share used is carried in a field named for the share left"
    source: "`binance_adapter.py` 2397 assigning the figure from 2330"
  - claim: "A replay's venue does none of this"
    source: "`replay_venue_adapter.py` 398-417 and 427"
---
# Holding back sends

Praxis limits how fast it calls the exchange, by keeping a store of permits that refills steadily and is capped. A call takes one. Where the store is empty, the caller waits, then goes.

This sits in front of the exchange's own limits rather than instead of them. Praxis slows itself down; the exchange may still refuse.

## What the wait is

The wait is worked out once and not looked at again. It counts the permits others have already taken, so a second caller arriving at an empty store waits longer than the first, rather than both waiting the same.

A call given up on before it goes hands its permit back — though a caller already sleeping on a wait that counted it keeps on sleeping.

## Waiting without blocking

The store is held only long enough to take a permit and work out the wait. The waiting happens after letting go, so a caller that must wait does not hold everyone else behind it.

## What the exchange says

Three kinds of call take a permit. Asking the exchange the time takes none, and reads no allowance either.

The allowance used is read from the answers that carry it, and from that comes the share [a health report](health.md) carries. That share is the part **used**, though the field it travels in is named for the part left — [recorded](../register.md) as H-054. A figure of six thousand stands until the venue says otherwise, and an answer carrying no limits leaves whatever is already known; where the limit is nothing or less, nought is reported instead of a share.

[A replay's venue](the-replay-venue.md) does none of this.

## Related

- [Health](health.md)
- [What a venue is](what-a-venue-is.md)
