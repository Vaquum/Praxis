---
row: P4-09
baseline: 49aa659
created: 2026-10-03 16:39 UTC
modified: 2026-10-11 07:15 UTC
evidence:
  - claim: "Six kinds of change answer the seven ways of working, the two fixed-pace ways sharing one"
    source: "`modify_params.py` 31-39, the ways listed at `praxis/core/domain/enums.py` 119-125"
  - claim: "That mirrors how the settings are registered"
    source: "`execution_params.py` 30-38"
  - claim: "A change carries the command's name, the account and a reason, each of which must be something rather than nothing"
    source: "`trade_modify.py` 45-46 into `_require_str.py` 28-30"
  - claim: "Its moment must carry a zone and an offset"
    source: "`trade_modify.py` 48-50"
  - claim: "Every field of every kind may be left unset"
    source: "`single_shot_modify.py` 31-33, `bracket_modify.py` 37-41, `iceberg_modify.py` 29-30, `interval_slice_modify.py` 31-32, `scheduled_vwap_modify.py` 36-37, `ladder_dca_modify.py` 36-37"
  - claim: "Every kind refuses a change with nothing set at all"
    source: "`single_shot_modify.py` 41-43, `bracket_modify.py` 55-57, `iceberg_modify.py` 38-40, `interval_slice_modify.py` 38-40, `scheduled_vwap_modify.py` 43-45, `ladder_dca_modify.py` 43-45"
  - claim: "Where a price or an amount is given, it must be a finite decimal above nought"
    source: "`single_shot_modify.py` 45-51, `bracket_modify.py` 67-73, `iceberg_modify.py` 42-48, `scheduled_vwap_modify.py` 52-58"
  - claim: "A ladder's levels are held the same way"
    source: "`ladder_dca_modify.py` 48-55"
  - claim: "So are its weights"
    source: "`ladder_dca_modify.py` 65-76"
  - claim: "A count of parts and a gap are whole numbers rather than decimals"
    source: "`interval_slice_modify.py` 42-56"
  - claim: "A single order's original price settings allow an endless price, where its change refuses one"
    source: "`single_shot_params.py` 38-42 against `single_shot_modify.py` 45-51"
  - claim: "A weighted change naming weights is refused as it is submitted, by a raise the caller sees"
    source: "`validate_trade_modify.py` 210-218, called at `execution_manager.py` 3060-3065"
  - claim: "A change naming a command already ended, with no bracket of its own left, takes an earlier road, which logs and returns rather than raising"
    source: "`validate_trade_modify.py` 171-175 into `execution_manager.py` 3067-3072"
  - claim: "Where one reaches the handler anyway, it is turned away before any gap on it is reached"
    source: "`execution_manager.py` 10101-10107"
  - claim: "The gap is read only past that point"
    source: "`execution_manager.py` 10109-10113 into 10189-10199"
  - claim: "Such a turning-away makes no outcome and calls nobody back"
    source: "`execution_manager.py` 10101-10107 against the queue it was taken from at 3938-3951"
---
# The change each way of working accepts

A [change](changing-work-already-sent.md) carries its own settings, as [a command](what-a-command-must-carry.md) does. Six kinds answer the seven [ways of working](ways-of-working-a-host-may-drive.md), the two fixed-pace ways sharing one, which mirrors how the settings themselves are registered.

## What every change carries

The name of the command being changed, the account, and a reason — each of which must be something rather than nothing. A moment that carries a zone and an offset.

## What every kind has in common

Every field of every kind may be left unset, since a change names only what it alters. So every kind refuses a change with nothing set at all, there being nothing to do.

Where a price or an amount is given, it must be a finite decimal above nought. A count of parts and a gap in seconds are whole numbers instead, and held to their own bounds.

A single order is the one place a change is stricter than the settings it replaces: those settings allow an endless price, and the change refuses one.

## A weighted change naming weights

It is refused as it is submitted, by a raise the caller sees, so the weights are never applied — unless the command it names has already ended with no bracket of its own left, which is caught earlier and merely logged.

Should one reach the handler by another road, it is turned away there before any gap on it is reached — a change asking for both loses the gap along with the weights, and that turning-away makes no outcome and calls nobody back.

## Related

- [What each change insists on](what-each-change-insists-on.md)
- [Changing work already sent](changing-work-already-sent.md)
