---
row: P20-01
baseline: 49aa659
created: 2026-11-08 15:33 UTC
modified: 2026-11-08 15:34 UTC
evidence:
  - claim: "A sell's change is answered no before anything else is read"
    source: "`validate_trade_modify.py` 97-98"
  - claim: "A ladder's change is sent down a road of its own"
    source: "`validate_trade_modify.py` 100-107"
  - claim: "For the rest, the prices weighed are the ones listed for that way of working, and only two ways of working have any listed"
    source: "`validate_trade_modify.py` 109-110, the lists at 26-29"
  - claim: "A named price above its original raises"
    source: "`validate_trade_modify.py` 127-128"
  - claim: "A named price with no original to weigh against raises"
    source: "`validate_trade_modify.py` 117-118"
  - claim: "A change that trips none of this is answered no, and the change goes on to be queued"
    source: "`validate_trade_modify.py` 130, the answer read at 220"
  - claim: "The second price listed for a single order cannot be reached, a change naming it being refused earlier"
    source: "`validate_trade_modify.py` 27 against 200-203, raising at 204-208 before 220"
  - claim: "The branch for a price that arrives as a row of figures cannot be reached either, since both listed fields are refused unless they are single exact figures"
    source: "`validate_trade_modify.py` 120-125, the fields held to single figures at `praxis/core/domain/single_shot_modify.py` 45-51 and `praxis/core/domain/iceberg_modify.py` 42-48"
---
# What counts as raising what a buy commits

[A change](changing-work-already-sent.md) is refused where it raises what a buy commits above the original. What counts as raising it is decided before the change is queued, from what the change names and what the original carried.

## What is not weighed

A sell. The deciding answers no before reading anything else, since a sell commits coin the account already holds.

A way of working with no commitment prices listed for it. Only two have any listed: a single order, and [an iceberg](part-shown-orders.md). For every other way the deciding reads nothing and answers no — [a ladder](work-fed-out-over-time.md) excepted, which is sent down [a road of its own](how-a-ladders-change-is-weighed.md).

## What raises it

A named price above the original raises it.

So does a named price with no original to weigh it against: there is nothing to bound it by, and the change is turned back rather than let through.

A change that trips none of this is answered no, and goes on to be queued.

## The two paths nothing reaches

A single order lists two prices here, its resting price and its stop-limit price. A change to a single order naming a stop price or a stop-limit price is refused outright, several steps earlier, so the second of the two can never reach this deciding.

The deciding also carries a branch for a price arriving as a row of figures, which compares the rows rung by rung. Both listed fields are refused unless they are single exact figures, so no row can arrive on this road. The ladder, which does have rows, never comes this way.

## Related

- [Changing work already sent](changing-work-already-sent.md)
- [How a ladder's change is weighed](how-a-ladders-change-is-weighed.md)
- [The change each way of working accepts](the-change-each-way-of-working-accepts.md)
