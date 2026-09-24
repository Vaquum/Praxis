---
row: P1-05
baseline: 49aa659
created: 2026-09-20 16:58 UTC
modified: 2026-09-24 08:02 UTC
evidence:
  - claim: "Every other kind is routed elsewhere before this path"
    source: "`execution_manager.py` 3994-4009, with a defensive refusal for anything that still arrives at 4170-4188, returning instead of reaching the fetch at 4192-4197"
  - claim: "The book is fetched only after the drop and mode checks have let the order past"
    source: "dropped at `execution_manager.py` 4154-4168, or refused for its mode at 4170-4188, otherwise fetched at 4192-4197"
  - claim: "A failed book request leaves no figure and no comparison is made"
    source: "`execution_manager.py` 4222-4228 leaving the estimate unset"
  - claim: "Work fed out or laddered is ended unstarted past its deadline"
    source: "either `execution_manager.py` 3995-3996 or 4004-4005, both into 4123-4129"
  - claim: "A bracket or hidden-size order has no such deadline test"
    source: "either `execution_manager.py` 4000 or 4002"
  - claim: "For a sell the figure is flipped in sign before the comparison"
    source: "`execution_manager.py` 4081-4085"
  - claim: "A figure within the maximum lets the order through"
    source: "`execution_manager.py` 4087-4088, returning no reason, so the send follows at 4268-4280"
  - claim: "The limit is one setting for the whole host, not part of the order"
    source: "`execution_manager.py` 680 with 4064-4065"
  - claim: "Only a market order, and only where the maximum is configured, can be stopped by any of this"
    source: "`execution_manager.py` 4064-4065"
  - claim: "No figure stops such an order"
    source: "`execution_manager.py` 4067-4079"
  - claim: "Being stopped ends the work unsent"
    source: "`execution_manager.py` 4232-4240"
---
# The likely-price check

Before a plain single [order](what-a-trade-is.md) is sent, Praxis tries to compare [what it would likely average](how-the-likely-price-is-worked-out.md) against the middle of the order book, and can refuse the order on the result.

Anything asking to be fed out over time, laddered, given a separate display size, or wrapped with protection is queued the same way but carried out along its own path, and never reaches this check. Work fed out or laddered is ended unstarted if its deadline has already passed; a bracket or a hidden-size order is not checked for that.

## The comparison

The figure is how far the average sits above the middle, counted in hundredths of one percent. For a buy it is used as it stands; for a sell it is flipped in sign first, so that either way a worse price gives a bigger number. That is what gets compared against the limit.

## What it can do

Every order that gets as far as [sending](how-an-order-is-placed.md) is put through the working-out; one already dropped by [a cancellation](how-a-trade-is-cancelled.md) never is. Asking the venue for the book can itself fail, and then there is no figure to judge.

Only a market order can be stopped by the result, and only where the host has been given a maximum deviation to allow. Such an order is stopped when the figure beats that maximum, and stopped too when there was no figure at all; a figure within the maximum lets it through. Every other order is sent whatever came back.
