---
row: P70-06
baseline: 49aa659
created: 2026-11-13 02:00 UTC
modified: 2026-11-13 02:00 UTC
evidence:
  - claim: "The refusal of money at the head of the settings run is reached only by a way of working that permits a market order"
    source: "`validate_trade_command.py` 341, reached past 170-175"
  - claim: "Four ways of working permit a market order alone and so reach it: the bracket, the evenly spread order, the weighted order and the order that spreads buying over time"
    source: "`validate_trade_command.py` 38-42, and 43-47, and 48-52, and 58-62"
  - claim: "Two permit a limit order alone: the hidden order and the ladder"
    source: "`validate_trade_command.py` 53-57, and 63-67"
  - claim: "A command of either of those two sized in money and sent as a limit order fails the market requirement in the shape check"
    source: "`validate_trade_command.py` 170-175"
  - claim: "Sent as a market order it fails the kind check, which stands before the shape check"
    source: "`validate_trade_command.py` 195-200, reached from 132 ahead of 134"
  - claim: "So that refusal cannot be met by a hidden order or a ladder, however it is sized or sent"
    source: "`validate_trade_command.py` 341 standing past both 195-200 and 170-175"
---
# Which modes the money refusal reaches

The run over a way of working's own settings begins by refusing a command sized in money, and two of the six ways of working can never get that far.

## The four that reach it

The bracket, the evenly spread order, the weighted order, and the order that spreads buying over time. Each permits a market order alone — which is what a command sized in money must be — so such a command passes the kind check and the shape check, and meets the refusal in the settings.

## The two that cannot

The hidden order and the ladder. Each permits a limit order alone.

A command of either, sized in money and sent as a limit order, fails the requirement that money means a market order — in the shape check, one step earlier.

Sent as a market order instead, it fails the kind check, which stands one step earlier still.

So the refusal in the settings cannot be met by a hidden order or a ladder, however such a command is sized or sent.

## Why it is written anyway

The refusal is written once, at the head of a run shared by all six. Reading it as a rule about all six is the natural reading and the wrong one: for two of them it is unreachable, and the rule is enforced for those two by the checks that come before.

## Related

- [What a command sized in money is held to](what-a-command-sized-in-money-is-held-to.md)
- [Where the order type decides](where-the-order-type-decides.md)
