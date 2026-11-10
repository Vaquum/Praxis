---
row: N67-02
baseline: 49aa659
created: 2026-11-08 20:17 UTC
modified: 2026-11-08 20:17 UTC
evidence:
  - claim: "Each of the two mappings is held to being a mapping where it is given, and left alone where it is not"
    source: "`nexus/strategy/action.py` 111-114, and 121-124"
  - claim: "A mapping that passes is copied and the copy put behind a reading-only view, which is written over the field by the means that goes round the sealing"
    source: "`nexus/strategy/action.py` 115-119, and 128-132"
  - claim: "So a caller altering the mapping it handed in reaches nothing the action holds"
    source: "`nexus/strategy/action.py` 118, copying what was handed in"
  - claim: "The copy reaches the mapping and not what it holds, so a value inside it stays shared with the caller"
    source: "`nexus/strategy/action.py` 118, copying one level"
  - claim: "The parameters for the way of working may be a mapping with nothing in it, and the parameters for a change may not"
    source: "`nexus/strategy/action.py` 111-119 asking nothing of the size, against 125-127"
  - claim: "An action given neither mapping carries nothing in their place, and the kind's own requirements are what ask for one"
    source: "`nexus/strategy/action.py` 111 and 121 passing over an absent mapping, with the asking at 234-235"
---
# The two mappings an action reseals

[An action](what-a-strategys-action-is-checked-for.md) can carry two mappings — the parameters for its way of working, and the fields a change is to rewrite — and each is replaced as the action is built.

## What the replacing does

A mapping that is given must be a mapping. One that passes is copied, the copy put behind a view that can only be read, and that view written over the field by the means that goes round the sealing.

So a caller that alters the mapping it handed in reaches nothing the action holds, and a caller handed the action back cannot write into either mapping at all.

## How far it reaches

The copy reaches the mapping and not what the mapping holds. A value inside it — a list, a record, another mapping — stays shared with the caller, and altering that reaches what the action holds.

## Where the two differ

The parameters for the way of working may be a mapping with nothing in it. Nothing asks about their size.

The parameters for a change may not. An empty one is refused, by a test the other mapping has no counterpart for.

## Absent

An action given neither carries nothing in their place. Which kinds of action need one is settled by [the kind's own requirements](what-each-kind-of-action-requires.md) rather than here, and a change is the one kind that asks.

## Related

- [What a strategy's action is checked for](what-a-strategys-action-is-checked-for.md)
- [What each kind of action requires](what-each-kind-of-action-requires.md)
