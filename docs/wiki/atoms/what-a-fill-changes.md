---
row: P2-29
baseline: 49aa659
created: 2026-09-26 05:58 UTC
modified: 2026-09-27 10:57 UTC
evidence:
  - claim: "Two running pictures are updated, one after the other"
    source: "`execution_manager.py` 2081 and 2086-2087"
  - claim: "A failure updating the first leaves the second untouched"
    source: "`execution_manager.py` 2081, ahead of 2086-2087"
  - claim: "The first keeps the order and the holdings"
    source: "`trading_state.py` 402-403"
  - claim: "The second keeps money, lots and profit, and a failure updating it is logged and passed over"
    source: "applied at `account_ledger.py` 112-113, the failure caught at `execution_manager.py` 2092-2098"
  - claim: "It covers one trading pair and refuses any other"
    source: "`account_ledger.py` 244-246"
  - claim: "It refuses a fee charged in an asset it does not know"
    source: "`account_ledger.py` 314-316"
---
# What a fill changes

A [fill](what-a-fill-is.md) the record has accepted updates two running pictures in turn. They keep different things, and the order matters: a failure updating the first leaves the second untouched, so the money picture only ever sees fills the first picture took.

## The order and the holdings

The first keeps [the order](fills-and-the-order.md) and [the holdings](holdings.md).

A failure there is not swallowed where it happens. It travels back out, and [what becomes of it](when-an-update-fails.md) turns on where it was raised — anything from one instruction being abandoned to the [account](what-an-account-is.md) being stopped outright.

## The money

The second keeps the account's money, its groups of purchases and its profit.

A failure there is written to the log and passed over, so trading carries on with the money picture left behind.

It covers one trading pair and refuses any other, and refuses a fee charged in an asset it does not know — and both of those refusals are passed over the same way. Adding a second symbol would therefore stop this picture keeping up, quietly, while trading went on.

## Related

- [When an update fails](when-an-update-fails.md)
- [Fills and the order](fills-and-the-order.md)
