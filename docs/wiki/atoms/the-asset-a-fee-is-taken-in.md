---
row: P65-06
baseline: 49aa659
created: 2026-11-12 23:30 UTC
modified: 2026-11-12 23:30 UTC
evidence:
  - claim: "The asset is chosen by side: the base one on a buy, or the quote one on a sell"
    source: "`ledger.py` 138"
  - claim: "A fill naming no asset is given that choice"
    source: "`ledger.py` 415-416"
  - claim: "A fill naming an asset must name the one the choosing would have made, and is refused otherwise"
    source: "`ledger.py` 418-422"
  - claim: "So a buy naming the quote asset is refused, and a sell naming the base asset is"
    source: "`ledger.py` 418 against 138"
  - claim: "The road an order takes offers no asset of its own and writes the chosen one into every fill"
    source: "`ledger.py` 567"
  - claim: "The two assets the simulated venue knows are declared once and are the only ones a fee can be in"
    source: "`ledger.py` 117, and 118, read by the choosing at 138"
---
# The asset a fee is taken in

A fee in [binsim's ledger](binsims-ledger.md) is taken in the base asset on a buy and the quote asset on a sell — whichever the side receives.

## How a caller meets that choice

A fill naming no asset is given the chosen one.

A fill naming an asset must name the one the choosing would have made. So naming it asserts the choice rather than making it: a buy naming the quote asset is refused, and so is a sell naming the base asset.

The road an order takes offers no asset of its own at all. The chosen one is written into every fill of the order, so an order cannot assert anything about it either.

## The two assets

The simulated venue knows two, declared once and read by the choosing. A fee can be in one of those two and nothing else, and which of the two is settled entirely by the side.

## Why it is worth knowing

A fee taken in the asset received is subtracted from the receipt rather than charged beside it, which is [what makes a buy deliver slightly less coin than its price suggests](what-settling-a-fill-moves.md).

A simulator charging in one asset throughout would leave a buy's whole quantity on the books, and every buy would then differ from the live behaviour by the fee's size.

## Related

- [What settling a fill moves](what-settling-a-fill-moves.md)
- [The guard a sell does not get](the-guard-a-sell-does-not-get.md)
