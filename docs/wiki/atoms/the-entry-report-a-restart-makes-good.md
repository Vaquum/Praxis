---
row: P175-02
baseline: 49aa659
created: 2026-11-16 08:00 UTC
modified: 2026-11-16 08:00 UTC
evidence:
  - claim: "A command already marked ended is passed over"
    source: "`execution_manager.py` 4786, then 4787"
  - claim: "The figures are the admitted totals kept for the command"
    source: "`execution_manager.py` 4790-4792"
  - claim: "The status is filled where the target is reached and part-filled otherwise"
    source: "`execution_manager.py` 4793, then 4794-4795"
  - claim: "The report carries an average price only where something has filled, and no reason"
    source: "`execution_manager.py` 4797-4808, the reason left empty at 4807"
  - claim: "It is reached only where the entry order has ended and filled above nothing"
    source: "`execution_manager.py` 4743, then 4748, then 4752"
  - claim: "The bracket is taken off the live brackets before the report is made"
    source: "`execution_manager.py` 4746, then 4752"
---
# The entry report a restart makes good

A bracket whose entry filled before a crash has that fill in the record and never told Nexus, and a restart tells it.

## Why it is owed

The replay puts the entry's fill back into the record. It does not send the report that fill would have caused, so Nexus is missing an entry it has every right to know about.

## When it is made

Only where the entry order has ended and filled above nothing. A command already marked ended is passed over — its report went out before the crash.

The bracket is taken off the live brackets before the report is made, so a second pass over them finds nothing to make good.

## What it says

The admitted totals kept for the command, with the status filled where the target is reached and part-filled otherwise. An average price only where something has filled, and no reason at all.

There is no third status here, where [a changed command's report](what-status-a-changed-command-reports.md) has one: this road is reached only once something has filled, so nothing-filled cannot arise.

## Related

- [What status a changed command reports](what-status-a-changed-command-reports.md)
- [What a restart puts back of a bracket](what-a-restart-puts-back-of-a-bracket.md)
- [What an outcome is](what-an-outcome-is.md)
