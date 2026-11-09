---
row: P95-02
baseline: 49aa659
created: 2026-11-09 07:34 UTC
modified: 2026-11-09 07:34 UTC
evidence:
  - claim: "A file with no old table at all is left alone"
    source: "`event_spine.py` 670 into 671"
  - claim: "A table holding nothing is dropped there and then"
    source: "`event_spine.py` 673, then 675 into 676-677, then 679"
  - claim: "A table holding rows demands the symbol the migration before recorded, and refuses without one"
    source: "`event_spine.py` 681, then 683 into 684-688"
  - claim: "The rows are then copied across under that symbol"
    source: "`event_spine.py` 690-691"
  - claim: "What arrived is read back and weighed against what was there"
    source: "`event_spine.py` 693, then 694"
  - claim: "Any row that did not arrive refuses the drop, naming how many are missing"
    source: "`event_spine.py` 696 into 697-701"
  - claim: "Only once every row is accounted for is the old table dropped"
    source: "`event_spine.py` 703-704"
---
# What the last migration drops

The last migration moves the old deduplication rows to their new table and drops the old one, and it will not drop it until every row is accounted for.

## The two easy roads

A file with no old table at all is left alone. A table holding nothing is dropped there and then, nothing needing to be moved.

## What a table with rows must have

The symbol the migration before recorded. Without one it refuses, naming how many rows carry no symbol it can use.

So the two migrations are a pair: the first proves there was exactly one symbol and writes it down, and the second will not move a row without it.

## The copying and the proving

The rows are copied across under that symbol. What arrived is then read back and weighed against what was there.

Any row that did not arrive refuses the drop, naming how many are missing. Only once every row is accounted for is the old table dropped.

## Why the proving is the point

Dropping the old table is the one step that cannot be undone by running the migration again. Everything before it can be repeated; the drop cannot.

So the check stands between the copy and the drop rather than after it, and a copy that lost rows leaves both tables in place for someone to look at.

## Related

- [What the first migrations add and prove](what-the-first-migrations-add-and-prove.md)
