---
row: P92-02
baseline: 49aa659
created: 2026-11-13 23:30 UTC
modified: 2026-11-13 23:30 UTC
evidence:
  - claim: "The amount filled is summed from the walk the book gave back"
    source: "`praxis/binsim/server.py` 474"
  - claim: "Each level of the walk is turned into a price, an amount and a fee"
    source: "`praxis/binsim/server.py` 478-487"
  - claim: "A buy's fee at a level is the amount times the rate, charged in the coin"
    source: "`praxis/binsim/server.py` 482-483"
  - claim: "Every other side's fee is the amount times the price times the rate, charged in the money"
    source: "`praxis/binsim/server.py` 484"
  - claim: "The check against the smallest worth is made on the amount filled, against a price read off the book"
    source: "`praxis/binsim/server.py` 489"
  - claim: "The ledger is then asked to apply the order under the caller's account and its own name"
    source: "`praxis/binsim/server.py` 491 into 492-495"
  - claim: "An account the ledger has no entry for is refused as an order turned away, rather than as a bad signature"
    source: "`praxis/binsim/server.py` 496 into 501-502"
  - claim: "The money the order came to is summed from the same levels, price times amount at each"
    source: "`praxis/binsim/server.py` 520, answered at 522-524"
---
# What a fill's fee is charged in

Binsim charges a fee at every level of the walk, and which asset it comes out of turns on the side.

## The levels

The amount filled is summed from the walk the book gave back. Each level of that walk is then turned into three things: a price, an amount, and a fee.

## The two fees

A buy's fee at a level is the amount times the rate, charged in the coin. Every other side's is the amount times the price times the rate, charged in the money.

So the same walk at the same prices costs a buyer coin and a seller money, and a reader comparing the two fees across a round trip is comparing figures in different assets.

## What is weighed after

The check against the smallest worth is made on the amount filled, against a price read off the book — so it weighs what the order actually got, rather than what it asked for.

## What the ledger is asked

To apply the order under the caller's account and the order's own name. An account the ledger has no entry for is refused as an order turned away, rather than as a bad signature.

So a caller whose signature resolved to an account binsim's ledger has never recorded is told its order was rejected, and learns nothing about the account.

## What the answer carries

The money the order came to, summed from the same levels, price times amount at each.

## Related

- [What a submitted order is weighed against](what-a-submitted-order-is-weighed-against.md)
- [The asset a fee is taken in](the-asset-a-fee-is-taken-in.md)
