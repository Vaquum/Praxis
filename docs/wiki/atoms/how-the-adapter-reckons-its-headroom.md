---
row: P108-01
baseline: 49aa659
created: 2026-11-09 08:25 UTC
modified: 2026-11-09 08:25 UTC
evidence:
  - claim: "The weight counted as used is whatever the last header said, until a window has passed since that header arrived"
    source: "`binance_adapter.py` 349, then 350 into 351, or 352"
  - claim: "Once that window has passed it reads as nothing at all, rather than decaying by degrees"
    source: "`binance_adapter.py` 350 into 351"
  - claim: "A weight limit at or below nought answers full headroom without any arithmetic"
    source: "`binance_adapter.py` 364 into 365"
  - claim: "Otherwise the headroom is what is left over the limit, held between nothing and everything"
    source: "`binance_adapter.py` 367"
  - claim: "The order headroom is reckoned the same way against its own limit, from a count kept per account"
    source: "`binance_adapter.py` 381, then 383 into 384, or 386"
  - claim: "That count is read with nothing standing in for an account never counted, so such an account reads as full"
    source: "`binance_adapter.py` 381, into 386"
---
# How the adapter reckons its headroom

The adapter reports how much of the venue's allowance is left as a fraction, and the weight it counts expires all at once rather than fading.

## What counts as used

Whatever the last header said, until a window has passed since that header arrived. Once it has, the used weight reads as nothing at all.

So there is no fading: the figure is the header's until the window closes, and then it is zero. Under steady traffic the expiry is never reached, because each fresh header replaces the figure and restarts its window.

## The headroom from it

A limit at or below nought answers full headroom without any arithmetic. Otherwise the headroom is what is left over the limit, held between nothing and everything — so a used figure larger than the limit reads as exhausted rather than as a negative.

## The order count

Reckoned the same way against its own limit, from a count kept per account. That count is read with nothing standing in where an account has no entry, so a fresh account reads as having full headroom.

The two differ in what they forget: the weight expires with its window, and the order count does not expire here at all.

## Related

- [What the adapter refuses to be told](what-the-adapter-refuses-to-be-told.md)
