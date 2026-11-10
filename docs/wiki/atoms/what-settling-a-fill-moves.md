---
row: P65-01
baseline: 49aa659
created: 2026-11-08 19:50 UTC
modified: 2026-11-08 19:50 UTC
evidence:
  - claim: "A buy takes the whole notional out of the quote balance and puts the quantity less the fee into the base one"
    source: "`ledger.py` 706-707"
  - claim: "A sell takes the quantity out of the base balance and puts the notional less the fee into the quote one"
    source: "`ledger.py` 709"
  - claim: "So the fee comes out of whichever asset the side receives, and is taken from the receipt rather than charged alongside it"
    source: "`ledger.py` 707, or 709, each subtracting the fee from what is credited"
  - claim: "Both new balances are worked out before either is weighed"
    source: "`ledger.py` 722-724"
  - claim: "The quote balance is weighed first and the base one second, each refused where it would stand below nought"
    source: "`ledger.py` 726-730, then 732-736"
  - claim: "Nothing is written until both have passed, the writing standing outside the working out"
    source: "`ledger.py` 738, written by the caller at 444-445"
  - claim: "A balance landing exactly on nought passes, the test asking only for below"
    source: "`ledger.py` 726, and 732"
---
# What settling a fill moves

Settling a fill against an account in [binsim's ledger](binsims-ledger.md) moves both balances at once, and which way each moves turns on the side.

## A buy

The whole notional comes out of the quote balance. The quantity, less the fee, goes into the base one.

## A sell

The quantity comes out of the base balance. The notional, less the fee, goes into the quote one.

## Where the fee falls

Out of the receipt rather than charged beside it, in [whichever asset the side receives](the-asset-a-fee-is-taken-in.md). So the fee never touches the asset being given up, and an account spending the whole notional on a buy receives slightly less coin than the price suggests.

## The two weighings

Both new balances are worked out before either is weighed. The quote one is weighed first and the base one second, and either standing below nought refuses the whole settling.

A balance landing exactly on nought passes: the test asks only for below. So a fill that spends an account down to nothing is allowed, and one that spends a hair past it is not.

## When the balances change

Not until both weighings have passed. The working out hands back a pair of figures, and the writing of them is a separate step, so a refused fill leaves both balances as they were.

## Related

- [Binsim's ledger](binsims-ledger.md)
- [The guard a sell does not get](the-guard-a-sell-does-not-get.md)
