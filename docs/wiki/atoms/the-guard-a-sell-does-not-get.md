---
row: P65-03
baseline: 49aa659
created: 2026-11-12 23:30 UTC
modified: 2026-11-12 23:30 UTC
evidence:
  - claim: "A buy whose fee stands at or above the quantity received is refused, before the ledger is touched"
    source: "`ledger.py` 407-413"
  - claim: "A sell has no matching test, its fee being held to being finite and to standing at or above nought and to nothing more"
    source: "`ledger.py` 393-396, and 404-405, with nothing weighing it against the notional in 393-424"
  - claim: "A sell's fee is taken out of the notional, so one above it makes the quote movement a debit"
    source: "`ledger.py` 709"
  - claim: "Such a sell gives up the quantity in base and pays in quote as well, both balances falling"
    source: "`ledger.py` 709 into 722-724"
  - claim: "It is refused only where one of those balances would stand below nought"
    source: "`ledger.py` 726-730, or 732-736"
  - claim: "The same pair of tests stands in the road an order takes, with the buy's test there and the sell's absent again"
    source: "`ledger.py` 518-524, within the walk at 503"
---
# The guard a sell does not get

A fee in [binsim's ledger](binsims-ledger.md) is taken out of what the side receives, and only one of the two sides is guarded against a fee that takes all of it.

## The buy's guard

A buy whose fee stands at or above the quantity received is refused before the ledger is touched. The complaint says why: a fee leaving no quantity behind is one the Praxis side will not accept either.

## The sell's absence

Nothing weighs a sell's fee against the notional it receives. The fee is held to being finite and to standing at or above nought, and to nothing more.

## What that allows

A sell's fee comes out of the notional. A fee above the notional therefore makes the quote movement a debit rather than a credit.

Such a sell gives up its quantity in base and pays in quote as well. Both balances fall, for a trade that was meant to bring money in.

It is refused only where one of the two balances would land below nought. An account holding plenty of quote can take such a sell, settle it, and come out lighter in both assets with a fill on its record saying it sold.

## The same gap on the other road

The road an order takes walks its fills and applies the same tests to each — the buy's guard among them, and the sell's still absent.

## Related

- [What settling a fill moves](what-settling-a-fill-moves.md)
- [Binsim's ledger](binsims-ledger.md)
