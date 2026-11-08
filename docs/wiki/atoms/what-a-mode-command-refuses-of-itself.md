---
row: P70-04
baseline: 49aa659
created: 2026-11-13 02:00 UTC
modified: 2026-11-13 02:00 UTC
evidence:
  - claim: "A command sized in money is refused first, before any settings are read"
    source: "`validate_trade_command.py` 341-343"
  - claim: "A command spreading buying over time must be a buy, refused with a complaint naming the side that arrived"
    source: "`validate_trade_command.py` 347-349"
  - claim: "An order hiding part of itself must not show more than the whole amount"
    source: "`validate_trade_command.py` 351-355"
  - claim: "A protective pair has the ordering of its two legs weighed by a check of its own"
    source: "`validate_trade_command.py` 357-358 into 361-394"
  - claim: "Two of the three later checks are reached by asking what kind the settings are, and the third by asking the way of working and the side"
    source: "`validate_trade_command.py` 351, and 357, against 347"
  - claim: "So an evenly spread order, a weighted one and a ladder meet nothing past the refusal of money"
    source: "`validate_trade_command.py` 347 and 351 and 357, none of them holding for those three"
  - claim: "The whole amount is read as already being there, by assertion rather than by a check, before the shown amount is weighed against it"
    source: "`validate_trade_command.py` 352, ahead of 353"
---
# What a mode command refuses of itself

A request naming any way of working other than the plain single order is weighed by one run of checks over its own settings.

## Money first

A command sized in money is refused before any settings are read at all. That is the first thing this run does, whatever way of working was named.

## Then by three narrower checks

Two of the three are reached by asking what kind the settings are. The third asks the way of working and the side instead.

A command spreading buying over time must be a buy, refused with a complaint naming the side that arrived — it exists to accumulate, and selling by it is turned away. That one asks the mode rather than the settings, because it shares its settings with the evenly spread order, which may sell.

An order hiding part of itself must not show more than the whole amount. The whole amount is read as already being there, by assertion rather than by a check, before the shown amount is weighed against it.

A protective pair has the ordering of its two legs weighed by a check of its own.

## What this run does not reach

An evenly spread order, a weighted one and a ladder meet nothing past the refusal of money. This run passes them untouched.

So it is not a list of rules every mode is held to. It is three narrow rules — two keyed on a shape of settings, one on a mode and a side — behind one rule that belongs to all of them.

## Related

- [The order a command's checks stand in](the-order-a-commands-checks-stand-in.md)
- [The settings each way of working takes](the-settings-each-way-of-working-takes.md)
