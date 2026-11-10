---
row: N23-02
baseline: 49aa659
created: 2026-11-08 15:48 UTC
modified: 2026-11-08 15:48 UTC
evidence:
  - claim: "The order of stages must be a tuple, of the same length as the list of stages, and must hold each of them exactly once"
    source: "`nexus/core/validator/pipeline_executor.py` 84-86, or 88 into 89-93, or 95-97"
  - claim: "The collection of checks must be a mapping"
    source: "`nexus/core/validator/pipeline_executor.py` 106-108"
  - claim: "A stage in the order with no check for it is refused"
    source: "`nexus/core/validator/pipeline_executor.py` 110-114"
  - claim: "A check the order names that cannot be called is refused"
    source: "`nexus/core/validator/pipeline_executor.py` 117-121"
  - claim: "Only the stages the order names are looked at, so an extra entry in the mapping is neither refused nor kept"
    source: "`nexus/core/validator/pipeline_executor.py` 117-118 and 122, walking the order rather than the mapping"
---
# What the walk is built from

[The walk that runs the checks](the-checks-a-decision-passes.md) is built from an order of stages and a check for each, and it refuses what it is given before it will run at all.

## What the order must be

A tuple. As long as the list of stages. And holding each of those stages exactly once — so an order repeating one and omitting another is refused by the third of those tests even where it passes the second.

## What the checks must be

A mapping. One with no check for a stage the order names is refused, and so is one whose check for a named stage cannot be called.

## What the order leaves out

The checks are read by walking the order. Each stage in the order is looked up in the mapping, and the mapping's own entries are never walked, so an entry under some other key is passed over: it goes unchecked, and it goes into nothing the walk keeps.

What the walk keeps is its own copy, one entry per stage in the order it was given, so the order it runs in is settled before any decision arrives.

## Related

- [The checks a decision passes](the-checks-a-decision-passes.md)
- [What a check must answer with](what-a-check-must-answer-with.md)
- [What each check weighs](what-each-check-weighs.md)
