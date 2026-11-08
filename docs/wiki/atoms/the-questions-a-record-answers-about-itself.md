---
row: P8-01
baseline: 49aa659
created: 2026-11-10 01:30 UTC
modified: 2026-11-10 01:30 UTC
evidence:
  - claim: "Three of the five accounts increase on the debit side and two do not"
    source: "`praxis/core/domain/chart_of_accounts.py` 27 into 43, the five at 20-24"
  - claim: "A command answers whether it was sized in quote units by whether it carries a quote amount at all"
    source: "`praxis/core/domain/trade_command.py` 77"
  - claim: "An order answers that same question the same way"
    source: "`praxis/core/domain/order.py` 84"
  - claim: "A position answers that it is closed where its amount stands equal to nought"
    source: "`praxis/core/domain/position.py` 78"
---
# The questions a record answers about itself

Four records on the Praxis side answer a question about themselves rather than refusing anything, and each answer is one line.

## Which way an account leans

Five accounts are named. Three increase on the debit side — the cash, the coin held, and the fees — and two do not: realized result and what was paid in.

A caller asking which way an account leans gets that from a fixed set of three rather than from anything about the entry being written.

## Whether a request was sized in money

A command answers that it was sized in quote units where it carries a quote amount at all. An order answers the same question the same way.

So the answer is the presence of a field. A record cannot say it was sized in money while carrying no amount in money, because the amount is the saying.

## Whether a position is closed

A position answers that it is closed where its amount stands equal to nought. The comparison is on the figure's value, so an amount written as nought to two places answers the same as a plain nought.

## Related

- [What a fill's own record requires](what-a-fills-own-record-requires.md)
- [The escape in the shared check for a name](the-escape-in-the-shared-check-for-a-name.md)
