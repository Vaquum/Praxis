---
row: P2-14
baseline: 49aa659
created: 2026-09-25 18:52 UTC
modified: 2026-09-25 19:13 UTC
evidence:
  - claim: "Eight kinds exist"
    source: "`enums.py` 66-73"
  - claim: "A market order names no price and no trigger"
    source: "`binance_adapter.py` 234-236"
  - claim: "The immediate limit order is a limit order the venue is told not to leave resting"
    source: "`binance_adapter.py` 240-242, with the instruction set at 817-818"
  - claim: "Four kinds rest on a trigger, two of them turning into limit orders"
    source: "`binance_adapter.py` 243-255"
  - claim: "The venue call builds most orders from one table of rules"
    source: "`binance_adapter.py` 233-256, read at 810-826, reached at 1542-1550"
  - claim: "Two sends skip it: a pair, and a market order sized in money"
    source: "either `binance_adapter.py` 1522-1536 for the pair, or 1505-1512 for the money-sized market order, whose params are built at 1570-1574"
  - claim: "The same kind sized in coin goes through the table"
    source: "`binance_adapter.py` 234-236 with the call at 1542-1550"
  - claim: "Which kinds are allowed depends on how the work is to be executed"
    source: "`validate_trade_command.py` 26-36, refused at 195-200"
---
# Order types

An **order type** says what kind of order goes to the [venue](what-a-venue-is.md). Praxis has eight.

A market order names no price and no trigger. A limit order names the price it will trade at and waits there. An immediate limit order is a limit order the venue is told not to leave resting. Four kinds wait for a trigger price to be reached, two of them then becoming market orders and two becoming limit orders. And a linked pair holds two of those orders together, so that the first to fill cancels the other.

Each kind also owns [the prices it must name](the-prices-an-order-must-name.md), and which kinds are allowed at all depends on how the work is to be executed.

## How a kind reaches the venue

The venue call builds most orders from one table of rules, which says what the venue calls each kind and which prices it carries.

Two sends skip that table. A pair is [sent, asked after and cancelled by calls of its own](where-the-order-type-decides.md). A market order sized in money rather than in coin has a builder to itself — though that same kind sized in coin goes through the table like the rest.

## Related

- [The prices an order must name](the-prices-an-order-must-name.md)
- [Where the order type decides](where-the-order-type-decides.md)
