---
row: P7-06
baseline: 49aa659
created: 2026-11-08 09:11 UTC
modified: 2026-11-08 09:11 UTC
evidence:
  - claim: "The record projecting a running scheme's state refuses nothing as it is built"
    source: "`praxis/core/domain/execution_scheme.py` 50-61"
  - claim: "The record holding a closed round-trip refuses nothing either, and nor does the one holding a replay's summary"
    source: "`praxis/replay/replay_report.py` 29-38, or 89-110"
  - claim: "The scheme's record answers whether it has ended by weighing its state against three named ones"
    source: "`praxis/core/domain/execution_scheme.py` 68, the three named at 22-26"
---
# The records that refuse nothing

Three Praxis records declare their fields and check none of them.

## The three

The record projecting a running scheme's state. The record holding one closed round-trip of a replay. The record holding a replay's summary over all of them.

Each declares what it carries and nothing more. A reader looking for the rules a figure on one of these must satisfy will find none, which is the fact worth having: whatever built the record decided, and the record keeps it.

## The one thing one of them answers

The scheme's record answers whether it has ended, by weighing its state against three named ones. That is the only question any of the three answers about itself.

## Related

- [What a replay reports](what-a-replay-reports.md)
- [What a restart puts back](what-a-restart-puts-back.md)
