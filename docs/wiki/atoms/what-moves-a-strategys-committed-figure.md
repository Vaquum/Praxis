---
row: N4-01
baseline: 49aa659
created: 2026-10-23 11:00 UTC
modified: 2026-10-23 12:10 UTC
evidence:
  - claim: "Ten places move the figure, and only one of them means to raise it: where money is set aside for a trade"
    source: "`nexus/core/capital_controller/capital_controller.py` 420, against 488-490, 522-524, 565-566, 688, 806, 963, 967, 1017 and 1079-1080"
  - claim: "What it adds there is the order's own amount and the fee guessed for it together"
    source: "`nexus/core/capital_controller/capital_controller.py` 324 into 420"
  - claim: "The figure is kept per strategy, read back by name and weighed against that strategy's budget where a new order asks for money"
    source: "`nexus/core/capital_controller/capital_controller.py` 328-330 into 378"
  - claim: "A fill moves it too, taking off the fee guessed for the part filled less the fee reported for it"
    source: "`nexus/core/capital_controller/capital_controller.py` 902-907, or 915-921, into 924 and 961-963"
  - claim: "A reservation that timed out, one handed back, and one found expired as the order is sent each take their own total back off"
    source: "`nexus/core/capital_controller/capital_controller.py` 488-490 under the time read at 480, 522-524, and 565-566 under the time read at 563"
  - claim: "An order refused and one cancelled each take their remaining total off, and so does an order given up on: one whose money had been taken but whose sending came apart, and one whose ending arrives with nothing of the order left to answer it"
    source: "`nexus/core/capital_controller/capital_controller.py` 688, 1017 and 1079-1080, the giving up at `praxis/launcher.py` 1989-1994, reached from `nexus/strategy/action_submit.py` 397-399, and at `praxis/launcher.py` 4476 and 4481 into 4484-4486"
  - claim: "A sale takes off what it released, which is the cost basis asked for or either figure where that is smaller"
    source: "`nexus/core/capital_controller/capital_controller.py` 800-806"
  - claim: "A fill that finishes an order leaving part of it unfilled takes that remainder off as well, the remainder being what the order still had against it"
    source: "`nexus/core/capital_controller/capital_controller.py` 915-922 into 965-967, the remainder worked out at `nexus/core/capital_controller/tracked_order.py` 123-129"
  - claim: "Every one of those moves goes through the same reading, which drops the strategy from the figures where what is left lands within a given amount of nought, or below it"
    source: "`nexus/core/capital_controller/capital_controller.py` 1097-1113"
  - claim: "That amount is a millionth of a millionth"
    source: "`nexus/core/domain/capital_state.py` 16, taken in at `nexus/core/capital_controller/capital_controller.py` 29"
  - claim: "A start replaces the figures outright rather than moving them"
    source: "`nexus/core/capital_controller/capital_controller.py` 258-271"
---
# What a strategy's committed figure moves on

A strategy's committed figure is the money set aside and committed against that strategy's trades, and ten places move it.

## The one that means to raise it

Money set aside for a trade adds the order's own amount and the fee guessed for it. That is the only move written to put money on.

## The ones that take it off

Three give back a reservation whole: one that timed out, one handed back, and one found expired as the order is sent. Three more give back an order's remaining total: one the venue refused, one cancelled, and one given up on — whose money had been taken but whose sending came apart, or whose ending arrived with nothing of the order left to answer it.

A sale takes off what it released — [the cost basis asked for, or either figure where that is smaller](what-a-taking-out-takes.md).

A fill that finishes an order leaving part of it unfilled takes that remainder off too.

## The one that can go either way

A fill also takes off the fee guessed for the part filled less the fee reported for it, which [can come to a rise](what-a-settling-fee-does-to-the-figure.md).

## What every move passes through

All ten go through one reading of the result. Where what is left lands within a millionth of a millionth of nought, or below it, the strategy is dropped from the figures rather than kept at a remainder.

A start moves nothing: it [works the whole set out again](what-a-boot-rebuilds-from-the-positions.md) and puts that in place of what was there.

## Related

- [How Nexus sets money aside](how-nexus-sets-money-aside.md)
- [What a taking-out takes](what-a-taking-out-takes.md)

---

Created 2026-10-23 11:00 UTC · Last modified 2026-10-23 12:10 UTC
