---
row: P4-36
baseline: 49aa659
created: 2026-10-03 17:11 UTC
modified: 2026-10-09 07:31 UTC
evidence:
  - claim: "An order's fields may be assigned, where a command's may not"
    source: "`order.py` 30 and 141-197 against `praxis/core/domain/trade_command.py` 29"
  - claim: "Assigning a size checks it is a finite decimal above nought"
    source: "`order.py` 157-165 and 173-181"
  - claim: "Assigning an amount of coin while an amount of money holds a value is refused"
    source: "`order.py` 166-171"
  - claim: "The refusal runs the other way too"
    source: "`order.py` 182-187"
  - claim: "The refusal turns on the value being something, so assigning nothing passes it"
    source: "`order.py` 166"
  - claim: "The test of the value does the same"
    source: "`order.py` 158"
  - claim: "So both can be empty at once, a state refused at the order's making"
    source: "`order.py` 99-101 against the assignments at 157-187"
  - claim: "Nothing requires the second half of such a swap, so the empty state need not be passing"
    source: "`order.py` 141-197"
  - claim: "Assigning the amount filled, or the running money, checks it is a decimal and not below nought, and nothing more"
    source: "`order.py` 189-195"
  - claim: "A moment assigned afterwards is not checked for carrying a zone"
    source: "`order.py` 141-197, the test made only at 93-97"
  - claim: "Nothing in this record's assignments checks the amount filled against the size"
    source: "`order.py` 141-197, the test made only at 133-135"
  - claim: "A fill beyond the size is added all the same, leaving what remains below nought"
    source: "`trading_state.py` 430 into `order.py` 215-218"
  - claim: "Nor is a price checked at all once assigned, by sign or by the kind of order"
    source: "`order.py` 141-197, the tests made only at 127-131 and 137-139"
---
# What changes on an order

[An order](the-order-record-praxis-keeps.md) is written to be changed. Its fields may be assigned, where [a command's](what-a-command-must-carry.md) may not, because the venue keeps reporting and the record keeps up.

## What assignment checks

Assigning either size checks the same thing the making does: a finite decimal above nought. Assigning one size while the other already holds a value is refused.

Assigning nothing to either is always allowed, both tests on a size turning on the value being something. So a size can be swapped — clear one, then set the other — and both can be empty at once in between, which is a state the order's making refuses outright. Nothing requires the second half, so that state need not be a passing one.

Assigning the amount filled, or the running total of money, checks it is a decimal and not below nought. Neither is checked for being finite.

## What assignment does not check

Two rules hold at the making and nowhere else.

The first is that the amount filled may not exceed the size. Assignment tests the amount for being a decimal and not below nought, and stops — so a fill beyond the size is added all the same, and what remains then reads below nought.

The second is about the prices. Once the record exists, neither price is tested again at all: not for its sign, and not against the kind of order. A resting price can be put on a market order afterwards.

Nor are the moments. One assigned later need not carry a zone, where one given at the making must.

## Related

- [The order record Praxis keeps](the-order-record-praxis-keeps.md)
- [Fills and the order](fills-and-the-order.md)
