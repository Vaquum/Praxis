---
row: P4-45
baseline: 49aa659
created: 2026-10-13 09:10 UTC
modified: 2026-10-13 09:10 UTC
evidence:
  - claim: "A sell is capped by the account's free coin and by what this trade owns of it"
    source: "`execution_manager.py` 7648 and 7656-7661"
  - claim: "A buy is capped by the free money over a price worked out for the cap alone, the best offer with a buffer on it"
    source: "`execution_manager.py` 7664-7665 into 6692, the buffer at 184"
  - claim: "The order itself goes out at the market, carrying no price, while that figure is also what the worth is weighed at"
    source: "`execution_manager.py` 7775 against 7783-7790, the figure kept at 7666 and weighed at 7681-7682"
  - claim: "A book query that raises, and a side with nothing on it, both leave the average paid going in as that price"
    source: "`execution_manager.py` 6686-6687 and 6689-6690, handed in at 7647 and 7664"
  - claim: "A sell's price is the best bid, falling back the same way"
    source: "`execution_manager.py` 7662 into 6708-6716"
  - claim: "What remains is rounded down to the venue's step"
    source: "`execution_manager.py` 7668"
  - claim: "Nothing caps the size at the largest the venue takes, so a size still over it after capping and rounding is refused by the adapter"
    source: "`execution_manager.py` 7668 and 7681-7690 against `binance_adapter.py` 1206-1210, reached from 1520"
  - claim: "A cap below the remainder is logged rather than refused"
    source: "`execution_manager.py` 7670-7679"
  - claim: "The size is weighed against that same price, and one under the smallest, or worth under the smallest value, sends nothing"
    source: "`execution_manager.py` 7681-7690"
---
# How big a flatten goes out

The size [a flatten](when-a-flatten-places-nothing.md) goes out at is what remains of the position, cut down to what the account can pay with and rounded to the venue's step.

## Capped by what is free

A sell is capped twice: by what the account holds free of the coin, and by what this trade owns of it — the free balance being the whole account's, which capping on alone would reach across.

A buy is capped by the free money over a price worked out for the cap alone: the best offer, with a buffer for fees and crossing. The order goes out at the market and carries no price, so that figure never reaches the venue — it decides the size, then whether the size is worth sending.

## When the book answers nothing

A query that raises, and a side with nothing on it, both leave the average paid going in as that price. It carries no buffer, so a buy can be sized above what the free money covers at the offer standing.

A sell is priced the same way off the best bid.

## Rounded, then weighed

What remains is rounded down to the venue's step. A cap below the remainder is logged rather than refused — and the rounded size is then weighed against that same price, one under the smallest the venue takes, or worth under its smallest value, sending nothing at all.

So a cap can shrink the order, and the shrinking can stop it.

Nothing here caps the size at the largest the venue takes. Capping and rounding can bring a large remainder under it anyway; what is still over goes out as it is, refused on the way by a check of the adapter's own.

## Related

- [When a flatten places nothing](when-a-flatten-places-nothing.md)
- [When protection is lost](when-protection-is-lost.md)
- [The sizes a venue trades in](the-sizes-a-venue-trades-in.md)

---

Created 2026-10-13 09:10 UTC · Last modified 2026-10-13 09:10 UTC
