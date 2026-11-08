---
row: N16-02
baseline: 49aa659
created: 2026-11-09 17:00 UTC
modified: 2026-11-09 17:00 UTC
evidence:
  - claim: "Three kinds of command are named"
    source: "`nexus/infrastructure/praxis_connector/trade_command_type.py` 23-25"
  - claim: "The mapping from action to command reaches two of the three"
    source: "`nexus/infrastructure/praxis_connector/translate.py` 20-25"
  - claim: "The third is weighed by the command record's own checks"
    source: "`nexus/infrastructure/praxis_connector/trade_command.py` 240"
  - claim: "The action that would need the third is refused by name instead"
    source: "`nexus/infrastructure/praxis_connector/translate.py` 75-81"
---
# The kind of command nothing builds

Three kinds of command are named, and the road that builds commands reaches two of them.

## The two it reaches

A new order, for an action that enters or exits. A cancel, for one that aborts or cancels. Four kinds of action, two kinds of command, each pair of actions sharing one.

## The third

The kind for amending an order. The command record checks what such a command must not carry, so the rules for one are written down. Nothing on this side builds one: the action that would need it is [refused by name](what-the-translation-refuses.md) before the mapping is reached.

So the record carries a set of checks for a shape this side never makes, and a reader meeting those checks is reading about a command the other side must build or nobody does.

## Related

- [What the translation refuses](what-the-translation-refuses.md)
- [What each kind of command must carry](what-each-kind-of-command-must-carry.md)
