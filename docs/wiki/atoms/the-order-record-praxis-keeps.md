---
row: P4-11
baseline: 49aa659
created: 2026-10-03 17:09 UTC
modified: 2026-10-04 11:43 UTC
evidence:
  - claim: "The record is made before the venue is called"
    source: "`execution_manager.py` 4264-4265 into `trading_state.py` 309-326, ahead of the placement that follows"
  - claim: "It carries two names, its own and the venue's, the venue's absent until the venue answers"
    source: "`order.py` 62-63, the venue's filled in at `trading_state.py` 341"
  - claim: "It carries the account and the command it came from, and the trading pair"
    source: "`order.py` 64-66"
  - claim: "Four of those names must each be something rather than nothing"
    source: "`order.py` 90-91 into `_require_str.py` 28-30"
  - claim: "When the record is made it carries exactly one of two sizes, an amount of coin or an amount of money"
    source: "`order.py` 99-101"
  - claim: "Whichever it carries must be a finite decimal above nought"
    source: "`order.py` 103-117"
  - claim: "It carries the amount filled and a running total of money, neither of which may be below nought"
    source: "`order.py` 119-125"
  - claim: "Both are added to as fills arrive, the money by amount times price"
    source: "`trading_state.py` 430-431"
  - claim: "A fill landing on a record already ended is added the same way"
    source: "`trading_state.py` 419-422"
  - claim: "The amount filled may not exceed the size when the record is made"
    source: "`order.py` 133-135"
  - claim: "It carries a commission, added to only where a buy's fee was charged in Bitcoin, tested by name"
    source: "`order.py` 78, added at `trading_state.py` 432 through the test at 66 and 84-87"
  - claim: "That commission is taken off the amount filled where a sell's size is worked out"
    source: "`execution_manager.py` 2639-2648"
  - claim: "It carries up to two prices, each tested by comparison alone when the record is made"
    source: "`order.py` 127-131"
  - claim: "A market order must carry no resting price when the record is made"
    source: "`order.py` 137-139"
  - claim: "When the record is made both its moments must carry a zone and an offset"
    source: "`order.py` 93-97"
  - claim: "The second is set afresh by the handlers that take the venue's news"
    source: "`trading_state.py` 343 and 433"
  - claim: "Four of its statuses count as ended"
    source: "`order.py` 22-27, read at 204"
  - claim: "What remains is the size less the amount filled, and nothing at all for an order sized in money"
    source: "`order.py` 215-218"
---
# The order record Praxis keeps

An **order** is what Praxis keeps about one attempt to place something at the venue. It is made before the placing, and [changes from there](what-changes-on-an-order.md) as the venue reports.

## Who it belongs to

Two names: the one Praxis built and the one the venue assigned, the venue's absent until it answers. Beside them the account, the command, and the trading pair. Four of those must each be something rather than nothing.

## What was asked for

When the record is made, exactly one of two sizes — an amount of coin, or an amount of money to spend — and it must be a finite decimal above nought.

Up to two prices, the resting price and the trigger. Each is tested by comparison alone, so an endless price gets in. A market order must carry no resting price. Both rules hold at the making, and not after.

## What has happened

The amount filled so far and a running total of what those fills cost, both added to as fills arrive — including a fill landing after the record has ended. Neither may be below nought, and at the making the amount filled may not exceed the size.

Separately a commission, but only where a buy's fee was charged in Bitcoin — tested by name, rather than against the pair being traded. A fee in anything else leaves it at nothing. Where it is there, it comes off the amount filled when [a sell is sized](the-commission-and-the-amount.md).

Then a status, four values of which count as ended, and two moments: when the record was made, and when it last changed. Both must carry a zone at the making.

What remains is the size less the amount filled, and nothing at all for an order sized in money.

## Related

- [What changes on an order](what-changes-on-an-order.md)
- [The commission and the amount](the-commission-and-the-amount.md)
