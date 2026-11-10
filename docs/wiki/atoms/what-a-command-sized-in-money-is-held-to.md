---
row: P70-03
baseline: 49aa659
created: 2026-11-08 21:00 UTC
modified: 2026-11-08 21:00 UTC
evidence:
  - claim: "The check answers at once for a command sized in coin, weighing nothing"
    source: "`validate_trade_command.py` 160-161"
  - claim: "One sized in money must be a buy, and the side is weighed before the kind of order"
    source: "`validate_trade_command.py` 163-168, ahead of 170-175"
  - claim: "It must then be a market order, refused with a complaint naming the kind that arrived"
    source: "`validate_trade_command.py` 170-175"
  - claim: "So within this check a sell is refused for its side whatever its kind, and the complaint about the kind is heard only for a buy"
    source: "`validate_trade_command.py` 163 standing ahead of 170"
  - claim: "The way of working is weighed against the kind of order before this check, so a command whose kind its mode forbids is refused for that first"
    source: "`validate_trade_command.py` 132 ahead of 134, refusing at 195-200"
  - claim: "Every way of working other than the plain single order refuses money outright, before anything else about the settings is weighed"
    source: "`validate_trade_command.py` 341-343, standing first in that run"
---
# What a command sized in money is held to

A request may say how much to spend rather than how much to buy, and three checks keep that to one case.

## The two on its shape

The check answers at once for a command sized in coin, weighing nothing at all.

One sized in money must be a buy. The side is weighed before the kind, so within this check a sell is refused for its side whatever kind of order it is.

The way of working is weighed against the kind of order before this check runs at all, so a command whose kind its mode forbids is refused for that first and never hears about its side.

It must then be a market order, refused with a complaint naming the kind that arrived. That complaint is therefore heard only for a buy.

## The one in the settings

Every way of working other than the plain single order refuses money outright, and does so before anything else about its settings is weighed.

[Which ways of working reach that refusal](which-modes-the-money-refusal-reaches.md) is not all of them.

## What is left allowed

One kind of order, on one side, under the plain single order.

The refusals that enforce it sit in three separate places — the kind check, the shape check, and the head of the settings check. A reader looking for the rule in any one of them finds part of it.

## Related

- [Where the order type decides](where-the-order-type-decides.md)
- [The order a command's checks stand in](the-order-a-commands-checks-stand-in.md)
- [Which modes the money refusal reaches](which-modes-the-money-refusal-reaches.md)
