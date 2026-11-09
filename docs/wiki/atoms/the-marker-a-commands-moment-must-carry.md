---
row: N11-02
baseline: 49aa659
created: 2026-11-08 01:05 UTC
modified: 2026-11-13 14:30 UTC
evidence:
  - claim: "A command refuses its moment unless that moment carries the UTC marker itself, so a zone standing at UTC is refused"
    source: "`nexus/infrastructure/praxis_connector/trade_command.py` 133-135, which tests the marker rather than the offset"
  - claim: "The two other handoffs the same connector makes accept any zone whose offset matches UTC's"
    source: "`nexus/infrastructure/praxis_connector/praxis_outbound.py` 252 into 253-254, and 307 into 308-309, each testing the offset"
---
# The marker a command's moment must carry

[A command's](what-a-command-is-checked-for.md) moment must carry the UTC marker itself, and a zone that merely stands at UTC is refused.

## The marker the test reads

Which marker the moment was built with. Two moments naming the same instant are treated differently where one was built with the marker and the other with a zone that happens to sit at the same offset.

## Where the same connector asks otherwise

The two other handoffs it makes test the offset instead, so each accepts the zone the command refuses. One record and the two sends beside it therefore disagree about what counts as UTC.

## Related

- [What a command is checked for](what-a-command-is-checked-for.md)
- [What each kind of command must carry](what-each-kind-of-command-must-carry.md)
