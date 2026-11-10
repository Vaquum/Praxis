---
row: N4-06
baseline: 49aa659
created: 2026-10-23 16:00 UTC
modified: 2026-10-25 09:00 UTC
evidence:
  - claim: "A fill works out the fee guessed for the part it filled less the fee reported for it"
    source: "`nexus/core/capital_controller/capital_controller.py` 902-907, or 915-921, into 924"
  - claim: "That figure is added to the fee held back and taken off the strategy's committed figure"
    source: "`nexus/core/capital_controller/capital_controller.py` 957 and 961-963"
  - claim: "Where the fee reported is the larger, the figure is below nought, so the one move is a raise and the other a draw on what was held back"
    source: "`nexus/core/capital_controller/capital_controller.py` 924, 957 and 963"
  - claim: "A shortfall overrunning the fee held back by more than a given amount fails the whole report before anything moves"
    source: "`nexus/core/capital_controller/capital_controller.py` 926-938"
  - claim: "That amount is a millionth of a millionth, and the guard reads strictly past it, so a shortfall can overrun an empty reserve by exactly that much and still go through"
    source: "`nexus/core/domain/capital_state.py` 16 read at `nexus/core/capital_controller/capital_controller.py` 926-938"
  - claim: "A fee held back left within that amount of nought is set to nought outright"
    source: "`nexus/core/capital_controller/capital_controller.py` 959-960"
---
# What a settling fee does to the figure

A settling fee is the difference between what a trade's fee was guessed at and what the report says it came to, and it can raise [a strategy's committed figure](what-moves-a-strategys-committed-figure.md) with no money set aside behind the rise.

## The two moves it makes

A fill works out the guess for the part it filled, less the figure reported for it. That difference goes two places at once: onto [the fee held back](what-the-fee-reserve-absorbs.md), and off the strategy's committed figure.

Where the guess was generous, the difference is above nought: the reserve grows and the committed figure falls. Where the report is the larger, the difference is below nought, and the two reverse — the reserve is drawn on and the committed figure rises.

## What stops it

A shortfall overrunning the reserve by more than a millionth of a millionth fails the whole report before anything moves. Below that margin it goes through, so a shortfall of a millionth of a millionth is settled against a reserve holding nothing at all, and the committed figure rises by it.

A reserve left within that same margin of nought is set to nought outright rather than carried as a sliver.

## Related

- [What a strategy's committed figure moves on](what-moves-a-strategys-committed-figure.md)
- [What the fee reserve absorbs](what-the-fee-reserve-absorbs.md)

---

Created 2026-10-23 16:00 UTC · Last modified 2026-10-25 09:00 UTC
