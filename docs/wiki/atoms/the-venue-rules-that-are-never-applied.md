---
row: P70-02
baseline: 49aa659
created: 2026-11-08 21:00 UTC
modified: 2026-11-08 21:00 UTC
evidence:
  - claim: "The one place that admits a request calls the checking with no venue rules, which is what both rule-weighing steps stand behind"
    source: "`execution_manager.py` 3479, against `validate_trade_command.py` 143 and 145"
  - claim: "The tests do hand rules in and reach both, so the steps are exercised there and nowhere else"
    source: "`tests/test_validate_trade_command.py` 482-485, and 647-665"
  - claim: "Were rules handed in, a command sized in money would be weighed against the smallest value alone and nothing else"
    source: "`validate_trade_command.py` 286-294"
  - claim: "A command sized in coin would have its amount weighed against the step, the smallest size and the largest, in that order"
    source: "`validate_trade_command.py` 298-300, then 302-304, then 306-308"
  - claim: "A price would be weighed only where the settings are a plain single order's and the kind is not a market order, against the step in price and then the smallest value"
    source: "`validate_trade_command.py` 310-311, then 313-316, then 318-320"
---
# The venue rules that are never applied

Half of what weighs a request at the door is written to take [the venue's own rules](the-sizes-a-venue-trades-in.md), and nothing hands them in.

## Why nothing reaches it

Both rule-weighing steps stand behind a test for rules having been given. The one place that admits a request calls the checking with none, so no request on that road reaches either.

The tests do hand rules in and reach both. So the steps are exercised, and never by a request.

## What it would weigh

A command sized in money: the smallest value the venue accepts, and nothing else — the step and the size bounds are about an amount of coin, which such a command does not carry.

A command sized in coin: the amount against the step, then the smallest size, then the largest, in that order.

A price: only where the settings are a plain single order's and the kind is not a market order, against the step in price and then the smallest value for the amount it buys.

[What it would weigh per child](what-the-per-child-rules-would-weigh.md) differs by shape.

## Where the weighing happens instead

Not here. Sizes and prices are brought to what the venue accepts elsewhere in the system — [a request is quantized as it is taken in](which-settings-are-refused.md), and an order is weighed again as it is built and sent. Which of those covers what this module would have covered is outside what this article accounts for.

## Related

- [The order a command's checks stand in](the-order-a-commands-checks-stand-in.md)
- [What the per-child rules would weigh](what-the-per-child-rules-would-weigh.md)
- [The sizes a venue trades in](the-sizes-a-venue-trades-in.md)
