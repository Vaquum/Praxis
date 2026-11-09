---
row: P70-01
baseline: 49aa659
created: 2026-11-08 21:00 UTC
modified: 2026-11-08 21:00 UTC
evidence:
  - claim: "The way of working is weighed against the kind of order first"
    source: "`validate_trade_command.py` 132"
  - claim: "The shape of a command sized in money comes next"
    source: "`validate_trade_command.py` 134"
  - claim: "A plain single order's settings are then weighed, or else the settings of whichever other way of working it names"
    source: "`validate_trade_command.py` 136-137, or 139"
  - claim: "The maker preference is weighed last of the checks that always run"
    source: "`validate_trade_command.py` 141"
  - claim: "The check for a plain single order answers at once where the settings are not that order's own kind"
    source: "`validate_trade_command.py` 215-217"
  - claim: "Settings of the wrong kind for the way of working named cannot arrive, the command's own record refusing them as it is built"
    source: "`praxis/core/domain/trade_command.py` 118-124"
  - claim: "The venue's own rules are weighed only where rules were handed in, and the per-child rules only then and only for a way of working other than the plain one"
    source: "`validate_trade_command.py` 143-144, then 145-146"
  - claim: "The one place that admits a request calls this with no rules at all, so neither is reached from there"
    source: "`execution_manager.py` 3479, the only call outside the tests"
---
# The order a command's checks stand in

A request admitted into [the trading side](what-turns-work-away.md) is weighed by one run of checks, in a fixed order, and the last two of them never run.

## The four that always run

The way of working is weighed against the kind of order. Then [the shape of a command sized in money](what-a-command-sized-in-money-is-held-to.md). Then the settings — a plain single order's, or else [those of whichever other way of working it names](what-a-mode-command-refuses-of-itself.md). Then the maker preference.

So a command wrong in two ways is refused for whichever comes first in that order, and a reader of a complaint learns the earliest thing wrong rather than the worst.

The check for a plain single order answers at once where the settings are not that order's own kind. That is a guard against something that cannot arrive: a command's own record refuses settings of the wrong kind for its way of working as it is built.

## The two that are conditional

The venue's own rules are weighed only where rules were handed in. The per-child rules are weighed only then, and only for a way of working other than the plain one.

## What hands them in

Nothing on the road a request takes. The one place that admits a request calls this with no rules at all, so [neither step is reached from there](the-venue-rules-that-are-never-applied.md).

## What that leaves

The four checks above are the whole of what a request meets here. Nothing about the sizes and prices the venue will accept is weighed at this door.

## Related

- [What turns work away](what-turns-work-away.md)
- [The venue rules that are never applied](the-venue-rules-that-are-never-applied.md)
- [What a command sized in money is held to](what-a-command-sized-in-money-is-held-to.md)
