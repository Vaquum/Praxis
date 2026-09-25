---
row: P2-27
baseline: 49aa659
created: 2026-09-25 19:01 UTC
modified: 2026-09-25 19:06 UTC
evidence:
  - claim: "A market order is the only kind the likely-price check can turn back"
    source: "`execution_manager.py` 4064-4065"
  - claim: "A market order is the only kind that may be sized in money"
    source: "`validate_trade_command.py` 170-175"
  - claim: "The venue call refuses that a second time"
    source: "`binance_adapter.py` 1485-1487"
  - claim: "The choice is made in five places and nowhere else"
    source: "the only such branches are `execution_manager.py` 4419, 5513 and 8520, and `praxis/trading.py` 723 and 977"
  - claim: "Cancelled by its own call when its deadline has passed"
    source: "either `execution_manager.py` 4420-4424 or 4426-4430"
  - claim: "Chased by its own lookup when a send goes unanswered"
    source: "`execution_manager.py` 5514-5516, rather than the single-order lookup at 5518-5523"
  - claim: "Cancelled by its own call on an ordinary cancel"
    source: "either `execution_manager.py` 8521-8525 or 8527-8531"
  - claim: "And on the sweep at shutdown and the reconciliation at the next start"
    source: "either `praxis/trading.py` 724-728 or 730-734, and either 978-982 or 984-988"
  - claim: "Only a resting limit order may have its price changed"
    source: "`execution_manager.py` 8680-8683"
  - claim: "A bracket's protective prices are changed by a different route"
    source: "routed away at `execution_manager.py` 8616-8620, handled at 9422-9500"
---
# Where the order type decides

Most of what happens to an order does not depend on [what kind it is](order-types.md). These are places where the kind alone changes the outcome.

## The market order

A market order is the only kind [the likely-price check](how-the-likely-price-is-checked.md) can turn back. The check is written to leave every other kind alone.

It is also the only kind that may be sized in money rather than in coin. An order of any other kind asking for that is refused on the way in, and refused a second time at the venue call if it somehow got that far.

## The linked pair

A linked pair is asked after and cancelled through calls meant for pairs, where a single order takes the ordinary ones. That choice is made in five places and nowhere else: when [its deadline passes](the-expiry-cancel.md), when [a send goes unanswered](when-a-send-is-unclear.md), when [it is cancelled outright](how-a-trade-is-cancelled.md), on the sweep that clears orders at shutdown, and on the reconciliation that clears leftovers at the next start.

## The resting limit order

A price change is refused for anything but a limit order still resting at the venue. That rule governs one path — a single order being amended. A bracket changing its protective prices is routed away before the rule is reached, and changes them by cancelling the pair and putting up a new one.

## Related

- [Order types](order-types.md)
