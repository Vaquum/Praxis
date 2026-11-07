---
row: N11-04
baseline: 49aa659
created: 2026-11-08 01:05 UTC
modified: 2026-11-08 01:05 UTC
evidence:
  - claim: "A new order must carry a side, a self-trade setting, and exactly one of a size or a spend"
    source: "`nexus/infrastructure/praxis_connector/trade_command.py` 227-229, or 230-232, or 233-235, or 236-238, all under the test at 226"
  - claim: "A change must carry none of the eleven things beyond the common ones, each refused on its own"
    source: "`nexus/infrastructure/praxis_connector/trade_command.py` 241-273 under the test at 240"
  - claim: "A cancel must carry none of those eleven either, refused the same way rather than by a check the two share"
    source: "`nexus/infrastructure/praxis_connector/trade_command.py` 276-308 under the test at 275"
---
# What each kind of command must carry

Each of the three kinds of command is held to its own list, weighed after [the checks every command makes](what-a-command-is-checked-for.md) have passed.

## A new order

It must carry a side, a self-trade setting, and exactly one of a size or a spend, which is to say one of the two and only one.

## A change, and a cancel

Neither may carry any of the eleven things a new order may: no side, no size, no spend, no self-trade setting, no way of executing, no kind of order, no settings, no deadline, no maker preference, no reference price, no strategy name.

## Written twice over

The two lists are the same eleven, and each kind has its own copy of them. A change is refused by one test and a cancel by another, rather than by a check they share.

## Related

- [What a command is checked for](what-a-command-is-checked-for.md)
- [The settings a command rewrites](the-settings-a-command-rewrites.md)
- [The marker a command's moment must carry](the-marker-a-commands-moment-must-carry.md)
