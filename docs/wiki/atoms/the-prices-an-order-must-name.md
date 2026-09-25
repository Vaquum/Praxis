---
row: P2-28
baseline: 49aa659
created: 2026-09-25 19:13 UTC
modified: 2026-09-25 19:13 UTC
evidence:
  - claim: "The rules are applied to a plain single order"
    source: "`validate_trade_command.py` 136-137, other ways of executing going to 139 instead"
  - claim: "Five kinds must name a price to trade at"
    source: "`validate_trade_command.py` 71-77, required at 219-223"
  - claim: "Five must name the trigger price they rest at"
    source: "`validate_trade_command.py` 81-87, required at 229-231"
  - claim: "The pair alone must name what its stop leg turns into"
    source: "`validate_trade_command.py` 98-102, required at 237-239"
  - claim: "Naming a price the kind has no use for is refused too"
    source: "either `validate_trade_command.py` 225-227, or 233-235, or 241-246, whichever price was named"
  - claim: "Protection Praxis builds itself may leave that last price unset"
    source: "passed through at `execution_manager.py` 4968-4977, omitted when absent at `binance_adapter.py` 872-874"
---
# The prices an order must name

Every [order type](order-types.md) owns a fixed set of prices. A plain single [order](what-a-trade-is.md) arriving from outside is checked against the set for its kind before it is accepted, and the rule runs both ways: the order is refused without a price its kind needs, and refused for naming a price its kind has no use for.

Work to be executed some other way — fed out over time, laddered, wrapped in protection — is checked by rules of its own.

## The three sets

Five kinds must name a price to trade at: the two limit orders, the two kinds that turn into limit orders on their trigger, and the pair.

Five must name the trigger price they rest at: the four kinds that wait for a trigger, and the pair.

The pair alone must also name the price its stop leg turns into once that trigger is reached.

## What never passes this way

Protection that Praxis puts up for itself is built inside the host and sent straight to the venue, so none of these rules is applied to it. Such a pair may leave that last price unset, and the venue call simply omits it.

## Related

- [Order types](order-types.md)
- [Where the order type decides](where-the-order-type-decides.md)
