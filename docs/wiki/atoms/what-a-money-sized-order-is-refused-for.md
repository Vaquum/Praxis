---
row: P111-01
baseline: 49aa659
created: 2026-11-09 08:35 UTC
modified: 2026-11-09 08:35 UTC
evidence:
  - claim: "A money-sized order takes a road of its own, chosen by that figure being given at all"
    source: "`binance_adapter.py` 1468"
  - claim: "That figure must be a finite decimal standing above nought"
    source: "`binance_adapter.py` 1470-1474 into 1475-1479"
  - claim: "An amount given alongside it is refused, exactly one of the two being required"
    source: "`binance_adapter.py` 1481 into 1482-1483"
  - claim: "Any kind but a market order is refused, and any side but a buy"
    source: "`binance_adapter.py` 1485 into 1486-1487, then 1489 into 1490-1491"
  - claim: "A stop figure of either kind is refused, and so is a price, and so is a time in force"
    source: "`binance_adapter.py` 1493 into 1494-1495, then 1497 into 1498-1499, then 1501 into 1502-1503"
  - claim: "What the road builds carries the caller's own name for the order only where one was given"
    source: "`binance_adapter.py` 1578 into 1579, answered at 1581"
  - claim: "An order with neither figure is refused on the other road"
    source: "`binance_adapter.py` 1514 into 1515-1516"
---
# What a money-sized order is refused for

An order sized in money rather than in coin takes a road of its own, and that road refuses seven things.

## How the road is chosen

By the money figure being given at all. So the choice is made on presence rather than on the kind of order, and everything the road refuses is refused after the choice is already made.

## The figure itself

It must be a finite decimal standing above nought.

## The six it will not have alongside

An amount, exactly one of the two being required. Any kind but a market order. Any side but a buy. A stop figure of either kind. A price. A time in force.

So the road accepts a market buy sized in money and nothing else, and each refusal names what it will not take rather than restating what it wants.

## Why the side is refused

The venue itself permits money-sizing only on a market buy. The refusal is this adapter declining to send what the venue would reject, with the venue's own limit as the reason.

## What it builds

Parameters carrying the caller's own name for the order only where one was given — the one thing the road takes that is not the money figure, the symbol or the side.

## The other road's own absence

An order with neither figure is refused there, so the two roads between them insist on exactly one.

## Related

- [What an order type decides about its parameters](what-an-order-type-decides-about-its-parameters.md)
