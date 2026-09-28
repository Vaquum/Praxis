---
row: P3-12
baseline: 49aa659
created: 2026-09-28 18:26 UTC
modified: 2026-09-28 18:26 UTC
evidence:
  - claim: "Lots are kept per trade, not pooled across the account"
    source: "`account_ledger.py` 322, sold from at 360"
  - claim: "One way of costing merges each buy into a single running lot"
    source: "`account_ledger.py` 324-328"
  - claim: "The other keeps a lot per buy"
    source: "`account_ledger.py` 332"
  - claim: "Which way is used is set when the account is registered"
    source: "`account_ledger.py` 239"
  - claim: "Registering a second time is refused"
    source: "`account_ledger.py` 236-237"
  - claim: "A sell takes from the lots in turn"
    source: "`account_ledger.py` 364-373"
  - claim: "A sell larger than the lots is refused after they have been taken"
    source: "`account_ledger.py` 375-377, past the taking at 364-373"
---
# Lots, and what a sell costs

A **lot** is what [the money ledger](the-money-ledger.md) remembers of a buy: an amount, at the price it was bought at. A sell is costed against the lots, which is how the ledger knows what a trade made.

Lots are kept under the [trade](what-a-trade-is.md) that bought them, rather than pooled across the account. Buys under another trade neither join them nor can cover their sells.

## Two ways of keeping them

Which way is used is set when the account is registered, and registering a second time is refused.

One way keeps a lot per buy, so a sell is costed against the oldest first. The other merges every buy for that trade into one running lot at a blended price, so a sell is costed at that blend.

## Selling more than is held

A sell takes from the lots in turn until its amount is covered, then checks whether the lots covered it.

That order matters. A sell larger than the lots hold is refused — but the taking has already happened, and nothing puts it back. The lots end empty, and the same sell tried again finds nothing left and fails a second time.

The failure itself is [logged and passed over](what-a-fill-changes.md), so trading carries on with the ledger's lots gone. This is [recorded separately](../register.md) as H-053.

## Related

- [The money ledger](the-money-ledger.md)
- [Holdings](holdings.md)
