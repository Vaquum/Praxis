---
row: P3-03
baseline: 49aa659
created: 2026-09-28 09:02 UTC
modified: 2026-09-28 17:13 UTC
evidence:
  - claim: "It is told a price to fill at, and refuses one that is not a real figure above zero"
    source: "`replay_venue_adapter.py` 107-111"
  - claim: "It takes only market orders"
    source: "`replay_venue_adapter.py` 179-183"
  - claim: "A send with no price set is refused"
    source: "`replay_venue_adapter.py` 186-192"
  - claim: "Asking for both an amount and a sum of money is refused"
    source: "`replay_venue_adapter.py` 202-204"
  - claim: "A sum of money is refused on a sell"
    source: "`replay_venue_adapter.py` 209-211"
  - claim: "What it accepts fills in full at that price"
    source: "`replay_venue_adapter.py` 232-237 and 255-258"
  - claim: "The fill comes back with the send itself"
    source: "`replay_venue_adapter.py` 258"
  - claim: "It keeps balances, charges a fee, and refuses a buy the balance cannot cover"
    source: "`replay_venue_adapter.py` 490-497"
  - claim: "Asked for a book it returns one level a side, at the price it holds, for no amount"
    source: "`replay_venue_adapter.py` 415-417"
  - claim: "No amount means the likely-price working-out can price nothing"
    source: "`estimate_slippage.py` refusing on depth, reached from `execution_manager.py` 4194-4197"
  - claim: "A plain single market order is then refused wherever a maximum has been set"
    source: "`execution_manager.py` 4064-4079, reached at 4230"
  - claim: "A market slice of work fed out over time never reaches that guard"
    source: "`execution_manager.py` 5979, which submits directly"
---
# The replay venue

The **replay venue** is what stands in for an exchange during a [replay](replay.md). It runs inside the same program and holds one price at a time, which the run sets to each bar's close before the strategy runs.

It takes market orders only. A price that is not a real figure above zero is refused, and so is a send arriving before any price is set.

## What it accepts fills at once

There is no waiting and no queue. A send it accepts fills in full at the price held, and the fill comes back with the send rather than later.

## What it still refuses

Asking for both an amount of coin and a sum of money is refused, and a sum of money is refused on a sell — the same shapes [the real venue call](what-a-venue-is.md) turns away.

It also keeps balances. A buy is charged a fee on top of the cost, and one the balance cannot cover is refused outright.

So a replay does catch work put together wrongly, and work that asks for more than the account has.

## The book it can be asked for

Asked for [an order book](the-order-book.md) it answers with a single level a side, at the one price it holds — and for no amount at either.

A price with no amount behind it is not depth. [Working out a likely price](how-the-likely-price-is-worked-out.md) needs amounts to walk down, so it can price nothing here.

Where a maximum deviation has been set for the host, [a plain single market order is then refused](how-the-likely-price-is-checked.md) — every one of them, for the whole run. A market slice of work fed out over time is sent straight to the venue and never meets that guard, so it trades as normal.

## Related

- [Replay](replay.md)
- [The replay clock](the-replay-clock.md)
