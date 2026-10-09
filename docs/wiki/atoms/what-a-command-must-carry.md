---
row: P4-07
baseline: 49aa659
created: 2026-10-03 13:07 UTC
modified: 2026-10-04 11:43 UTC
evidence:
  - claim: "A command is built from what the caller gave, then checked"
    source: "`execution_manager.py` 3461-3477 and 3479"
  - claim: "Assigning to a field of a built command is refused"
    source: "`praxis/core/domain/trade_command.py` 29"
  - claim: "A change to a ladder puts a rebuilt command in the old one's place, under the same name"
    source: "`execution_manager.py` 9345-9347"
  - claim: "A change to work fed out in slices alters its schedule instead, leaving the command where it is"
    source: "`execution_manager.py` 10149-10172"
  - claim: "A name the caller supplies must survive having its hyphens taken out and still run to sixteen characters"
    source: "`execution_manager.py` 3450 into `generate_client_order_id.py` 105-110"
  - claim: "It must also be unused by any command the host holds, whatever account it belongs to"
    source: "`execution_manager.py` 3452-3457 against the two stores made at 693 and 697"
  - claim: "Nothing waits between that test and the name being set aside, so two callers cannot both pass it"
    source: "`execution_manager.py` 3452-3457 ahead of 3522, undone at 3526-3529"
  - claim: "A caller supplying none has one made for it"
    source: "`execution_manager.py` 3458-3459"
  - claim: "Four names on the command must each be something rather than nothing"
    source: "`praxis/core/domain/trade_command.py` 83-84 into `_require_str.py` 28-30"
  - claim: "Exactly one of the two sizes must be given"
    source: "`praxis/core/domain/trade_command.py` 86-88"
  - claim: "Whichever is given must be a finite decimal above nought"
    source: "`praxis/core/domain/trade_command.py` 90-104"
  - claim: "The moment of making must carry a zone and an offset"
    source: "`praxis/core/domain/trade_command.py` 114-116"
  - claim: "Where the way of working registers a settings kind, the settings must be of it"
    source: "`praxis/core/domain/trade_command.py` 118-124"
  - claim: "That refusal comes while the command is being built, before the wider check is reached"
    source: "`praxis/core/domain/trade_command.py` 118-124 reached from `execution_manager.py` 3461-3477, ahead of 3479"
---
# What a command must carry

A **command** is one instruction to Praxis, built from what a caller gave and checked as it is built.

Assigning to a field of a built command is refused. A [change to a ladder](orders-at-several-prices.md) does not alter one: it puts a rebuilt command in the old one's place, under the same name. A change to [work fed out in slices](work-fed-out-over-time.md) alters that work's schedule instead, leaving its command where it is.

## Its name

A caller may supply the command's name. One supplied must survive having its hyphens taken out and still run to sixteen characters, so that [an order's name](how-an-order-is-named.md) can be built from it.

It must also be unused by any command the host holds — whatever account that command belongs to, since the two stores checked are kept for the host rather than per account. Nothing waits between the test and the name being set aside, so two callers cannot both pass it.

A caller supplying none has one made for it instead.

## What must be there

Four names must each be something rather than nothing: the command's own, the trade it belongs to, the account, and the trading pair.

Exactly one of the two sizes must be given — an amount of the coin, or an amount of money to spend. Giving both is refused, and so is giving neither. Whichever is given must be a finite decimal above nought.

The moment of making must carry a zone and an offset.

## Its settings

Where the chosen [way of working](ways-of-working-a-host-may-drive.md) registers a kind for [its settings](the-payload-a-modes-settings-arrive-in.md), the settings must be of that kind. That refusal comes while the command is being built, ahead of the wider check that follows.

## Related

- [What a command's checks let through](what-a-commands-checks-let-through.md)
- [What turns work away](what-turns-work-away.md)
