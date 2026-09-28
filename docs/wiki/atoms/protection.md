---
row: P2-21
baseline: 49aa659
created: 2026-09-28 06:24 UTC
modified: 2026-09-28 08:31 UTC
evidence:
  - claim: "The opening order is sent as a market order"
    source: "`execution_manager.py` 4521-4523 into `_submit_market_slice`"
  - claim: "Protection follows only once the opening order has finished"
    source: "`execution_manager.py` 4672-4673"
  - claim: "An opening order that filled nothing gets none"
    source: "`execution_manager.py` 4704-4712"
  - claim: "A part-filled one that finished does get it"
    source: "`execution_manager.py` 4704-4715"
  - claim: "The protective order goes on the side opposite the entry"
    source: "`execution_manager.py` 4909-4911"
  - claim: "It is a linked pair, one to take a profit and one to stop a loss"
    source: "`execution_manager.py` 4968-4977"
  - claim: "The first of the two to fill cancels the other"
    source: "`enums.py` 73 for the kind, sent as one at `binance_adapter.py` 1522-1536"
  - claim: "The profit price is given outright or worked out as a distance"
    source: "either `execution_manager.py` 5208-5209 or 5210-5217"
  - claim: "The stop price likewise"
    source: "either `execution_manager.py` 5218-5219 or 5220-5226"
  - claim: "The distance runs the other way for a sell entry"
    source: "`execution_manager.py` 5206, used at 5212-5215 and 5222-5225"
  - claim: "It is sized by what the holdings show, never above what the venue reported"
    source: "`execution_manager.py` 4849-4854"
  - claim: "Nothing held means nothing is sent"
    source: "zero returned at `execution_manager.py` 4851-4852, the sending given up at 4887-4904"
  - claim: "The record stays available for a later attempt"
    source: "`execution_manager.py` 4898, which returns before any flag is set"
  - claim: "A flag is set before the sending"
    source: "`execution_manager.py` 4906"
  - claim: "A second attempt turns back on finding it set"
    source: "`execution_manager.py` 4884-4885"
  - claim: "Three places place it, and all pass that guard"
    source: "`execution_manager.py` 4635, 4715 and 4753"
  - claim: "The record is kept with the pair's name on it, and a later change works from that"
    source: "named and kept at `execution_manager.py` 5031-5037, read at 9387 and used at 9429 and 9454-9455"
---
# Protection

The **protection** on a position is a pair of orders Praxis puts up after an opening order, to close that position out at either a good price or a bad one. The opening order and the protection together are asked for as one piece of work.

The opening order goes out as a market order. Protection follows only once that order has finished, and only where it filled something. A part-filled order that finished is protected for the part that filled; one that filled nothing gets none.

## The two prices

The protection is a [linked pair](order-types.md) on the side opposite the entry, so a buy is protected by sells. One takes a profit, the other stops a loss, and the first to fill cancels the other.

Each price is either given outright or given as a distance and worked out from the price the entry actually averaged. The distance runs one way for a buy and the other for a sell, so the profit sits on the far side and the stop on the near one.

## How much it covers

The protection is sized by what [the holdings](holdings.md) show, never above what the venue reported filled. Where nothing is held, nothing is sent and the record stays for a later attempt.

That matters because on some fills [the commission comes out of what the account receives](the-commission-and-the-amount.md). Sizing from the reported amount would then try to sell coin the account never got.

## Once it is up

A flag is set before the sending, so a second attempt turns back rather than putting up a second pair. Three places put protection up, and all pass that guard.

The record is kept afterwards with the resting pair's name on it, which is what a later change to those prices works from.

## Related

- [Order types](order-types.md)
- [Holdings](holdings.md)
