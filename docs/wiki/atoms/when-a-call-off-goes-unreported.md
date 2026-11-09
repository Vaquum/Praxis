---
row: P177-02
baseline: 49aa659
created: 2026-11-16 09:00 UTC
modified: 2026-11-16 09:00 UTC
evidence:
  - claim: "The call-off is recorded and applied before any report is worked out"
    source: "`execution_manager.py` 8540-8545, then 8546, then 8547, then 8549"
  - claim: "The figures are the admitted totals kept for the command"
    source: "`execution_manager.py` 8549-8551"
  - claim: "An average price is worked out only where something has filled, and left absent otherwise"
    source: "`execution_manager.py` 8552, then 8554 into 8555"
  - claim: "The trade's name is looked up, and a command with none remembered reports nothing at all"
    source: "`execution_manager.py` 8557, then 8558, then 8566"
  - claim: "Otherwise the report is built from those figures and the reason given"
    source: "`execution_manager.py` 8568-8576"
  - claim: "A trade's name is remembered on seven roads: a replayed intent, a resumed ladder, a resumed scheme, a command taken in, and the three closing commands"
    source: "`execution_manager.py` 1156, and 1386, and 2010, and 3566, and 5018, and 7815, and 8032"
---
# When a call-off goes unreported

Calling off an order writes the call-off down first and works the report out afterwards, so the two can part company.

## What is written

The call-off, recorded and applied, with the reason the call-off carried.

## What is reported

The admitted totals kept for the command, and an average price worked out only where something has filled.

The [trade's name](what-a-trade-is.md) is looked up to carry on the report. A command with none remembered reports nothing at all — the call-off stands in the record, the order is called off at the venue, and Nexus hears none of it.

## When that can happen

A trade's name is remembered on seven roads: a replayed intent, a resumed ladder, a resumed scheme, a command taken in, and the three commands that close a position. So the gap is an order whose command reached none of those roads in this run of the process.

## Related

- [How a trade is cancelled](how-a-trade-is-cancelled.md)
- [The command that ends twice](the-command-that-ends-twice.md)
- [What an outcome is](what-an-outcome-is.md)
