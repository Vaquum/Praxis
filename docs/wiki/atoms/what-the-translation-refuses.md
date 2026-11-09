---
row: N16-01
baseline: 49aa659
created: 2026-11-08 10:26 UTC
modified: 2026-11-08 10:26 UTC
evidence:
  - claim: "The translation refuses a decision that does not allow the action"
    source: "`nexus/infrastructure/praxis_connector/translate.py` 63-65"
  - claim: "It refuses a moment that does not carry the UTC marker itself"
    source: "`nexus/infrastructure/praxis_connector/translate.py` 67-69"
  - claim: "It refuses an empty reference for the command"
    source: "`nexus/infrastructure/praxis_connector/translate.py` 71-73"
  - claim: "It refuses a change outright, by name"
    source: "`nexus/infrastructure/praxis_connector/translate.py` 75-81"
  - claim: "Five kinds of action exist, its mapping names four of them, and the one left out is the change refused by name"
    source: "`nexus/infrastructure/praxis_connector/translate.py` 20-25 and 75-81, the five at `nexus/core/validator/pipeline_models.py` 36-40"
---
# What the translation refuses

Four refusals stand before the translation builds anything.

## The four

A decision that does not allow the action. A moment that does not carry [the universal-time marker](the-marker-a-commands-moment-must-carry.md) itself. An empty reference for the command. And a change, refused by name.

The change is turned back because this road does not carry one: a change that passed its checks goes out by a different call with its own parameters.

## Why the mapping needs no refusal of its own

Five kinds of action exist. The mapping names four of them, and the one it leaves out is the change the refusal above turns back. So every kind that reaches the mapping is in it, and the lookup past those four refusals cannot fail.

## Related

- [The kind of command nothing builds](the-kind-of-command-nothing-builds.md)
- [What an exit is given where it asked for nothing](what-an-exit-is-given-where-it-asked-for-nothing.md)
- [What a command is checked for](what-a-command-is-checked-for.md)
