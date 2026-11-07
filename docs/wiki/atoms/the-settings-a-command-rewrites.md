---
row: N11-03
baseline: 49aa659
created: 2026-11-08 01:05 UTC
modified: 2026-11-08 01:40 UTC
evidence:
  - claim: "Where a command is handed settings, it refuses anything that is not a mapping"
    source: "`nexus/infrastructure/praxis_connector/trade_command.py` 183 into 184-186"
  - claim: "Having accepted one, it writes a sealed copy of it over its own field"
    source: "`nexus/infrastructure/praxis_connector/trade_command.py` 187-192"
---
# The settings a command rewrites

Where [a command](what-a-command-is-checked-for.md) is handed settings it keeps a sealed copy of its own making.

## The mapping test, and the copy after it

Where settings are there at all, anything that is not a mapping is refused. A mapping is accepted — and then copied and sealed, and the copy written over the command's own field in place of what arrived.

## The sealed copy

Its own copy, sealed: nothing can be added to it, taken out of it, or put in place of what one of its keys already holds.

## Related

- [What a command is checked for](what-a-command-is-checked-for.md)
- [What each kind of command must carry](what-each-kind-of-command-must-carry.md)
