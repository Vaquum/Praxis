---
row: P165-02
baseline: 49aa659
created: 2026-11-16 03:00 UTC
modified: 2026-11-16 11:30 UTC
evidence:
  - claim: "A budget naming neither a size nor a spend is not recorded at all"
    source: "`execution_manager.py` 2383, then 2384"
  - claim: "Where a budget is already held for the command, the one offered is dropped and the first kept"
    source: "`execution_manager.py` 2386, then 2388, then 2407"
  - claim: "A second budget differing from the first is reported only where the caller asked for conflicts to be reported"
    source: "`execution_manager.py` 2389-2391"
  - claim: "Otherwise the budget offered is written under the command's name"
    source: "`execution_manager.py` 2409"
  - claim: "It is read back by the figure that caps a fill before the fill is counted"
    source: "`execution_manager.py` 2477, read from 2428"
  - claim: "Nothing in the recording revises the totals already counted"
    source: "`execution_manager.py` 2386, then 2407 against 2409"
  - claim: "One road of the four asks for conflicts, the one installing a command"
    source: "`execution_manager.py` 2345, then 2346, then 2350, against 1129, and 1158, and 4927"
---
# What a second budget offered for a command does

A command's budget is the size and spend its fills are [admitted against](the-part-of-a-fill-a-command-counts.md), and it is written once: a second offer for the same command is dropped and the first kept.

## Why the first is kept

The budget is read back by the figure that caps a fill before the fill is counted, so the totals standing against a command were measured by whichever budget was there at the time. The recording revises no total it finds already counted: it either writes a budget or keeps one. So the figure those totals were measured by is the figure that stays.

## What is offered and what is heard

A budget naming neither a size nor a spend is not recorded at all. One offered where none is held is written under the command's name.

A second one differing from the first is reported only where the caller asked for conflicts to be reported. Of the four roads that offer a budget, one asks: the road installing a command. The replay of a scheme's start, the replay of a submitted intent, and the budget of a closing order all offer theirs silently.

So a replay that offers a second budget differing from the first keeps the first without a word, and the record of the disagreement exists nowhere.

## Related

- [The part of a fill a command counts](the-part-of-a-fill-a-command-counts.md)
- [What a queue reservation is for](what-a-queue-reservation-is-for.md)
- [How a restart reads its record back](how-a-restart-reads-its-record-back.md)
