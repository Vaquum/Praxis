---
row: P3-13
baseline: 49aa659
created: 2026-09-30 05:58 UTC
modified: 2026-09-30 08:28 UTC
evidence:
  - claim: "Each way of working has one kind of change that fits it"
    source: "`modify_params.py` 31-39, matched at `validate_trade_modify.py` 193-198"
  - claim: "A single order may change the price it rests at, and a trigger price is refused"
    source: "`validate_trade_modify.py` 200-208"
  - claim: "Only a resting limit order is changed at all"
    source: "`execution_manager.py` 8680-8685"
  - claim: "Sliced work may change its count and its gap"
    source: "`interval_slice_modify.py` 31-32"
  - claim: "Weighted work may change only the gap, its weights refused and its count kept"
    source: "refused at `validate_trade_modify.py` 210-218, kept at `execution_manager.py` 10189-10199"
  - claim: "Protection has three prices that can change"
    source: "`execution_manager.py` 9871-9907"
  - claim: "A change naming an unknown request is refused"
    source: "`validate_trade_modify.py` 180-182"
  - claim: "A change naming another account's request is refused"
    source: "`validate_trade_modify.py` 184-189"
  - claim: "A change raising what a buy commits above the original is refused"
    source: "`validate_trade_modify.py` 220-226"
  - claim: "Every change passes those before being queued, protection included"
    source: "`execution_manager.py` 3060-3065"
  - claim: "A change to a request already finished normally does nothing further"
    source: "`execution_manager.py` 8622-8624"
  - claim: "A finished opening request whose protection is still live can still be named to change it"
    source: "`validate_trade_modify.py` 171-175, routed ahead of the finished test at `execution_manager.py` 8616-8620"
  - claim: "A change parked awaiting fills is not replaced by a second"
    source: "`execution_manager.py` 8631-8636"
  - claim: "Changes are processed one at a time"
    source: "`execution_manager.py` 3910-3939, queued without a check at 3060-3074"
---
# Changing work already sent

A **change** asks Praxis to alter work it has already accepted, rather than cancel it and start again. What may be altered depends entirely on how the work is being carried out, and each way of working has one kind of change that fits it.

A single order may change the price it rests at — and only if it is a limit order still resting; a trigger price cannot be changed at all. Work [fed out in slices](work-fed-out-over-time.md) may change how many parts and the gap between them, except where the parts are weighted, which may change only the gap. Work [at several prices](orders-at-several-prices.md) may change those prices and their weights. A [part-shown order](part-shown-orders.md) may change its shown amount and its price. [Protection](protection.md) has three prices that can change.

## What is refused on the way in

A change naming a request Praxis does not know is refused, and so is one naming a request belonging to another account.

A change that would raise what a buy commits above what the original committed is refused. Prices may move and parts be re-cut, but not so as to ask the account for more than it agreed to. A sell has no such limit, committing coin it already holds.

Every change passes those tests before being queued, protection included.

## Afterwards

A change reaching a request that has already finished normally does nothing further. A finished opening request whose protection is still live is the exception: it can still be named, to change that protection.

Two changes arriving together queue for processing one at a time. Where the first parks awaiting fills, the second does nothing when its turn comes.

## Related

- [Work fed out over time](work-fed-out-over-time.md)
- [Protection](protection.md)
