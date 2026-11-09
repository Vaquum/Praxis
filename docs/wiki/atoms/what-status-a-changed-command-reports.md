---
row: P168-02
baseline: 49aa659
created: 2026-11-16 04:30 UTC
modified: 2026-11-16 04:30 UTC
evidence:
  - claim: "The figures are the admitted totals kept for the command"
    source: "`execution_manager.py` 10426-10428"
  - claim: "An average price is worked out only where something has filled"
    source: "`execution_manager.py` 10429 into 10430-10431"
  - claim: "The target reached reports filled, something filled reports partial, and nothing filled reports pending"
    source: "`execution_manager.py` 10433, then 10434, or 10435, then 10436, or 10438"
  - claim: "The report is built from those figures and carries no reason"
    source: "`execution_manager.py` 10440-10448, the reason left empty at 10446"
  - claim: "It is sent after the fills the venue gave as it took the replacement are recorded"
    source: "`execution_manager.py` 10406, then 10407 into 10408, then 10410"
  - claim: "Those fills are recorded under the command the change belongs to, which is the command the totals are kept against"
    source: "`execution_manager.py` 10390-10405, the command named at 10397, read at 10426-10428"
---
# What status a changed command reports

A command whose order has been replaced reports a status worked out from one figure: how much the command has filled in all, across the order that was superseded and the one that replaced it.

## Where the figure comes from

The admitted totals kept for the command. The fills the venue gives as it takes the replacement are recorded under the command the change belongs to, which is the command those totals are kept against — so the two orders' fills are one running figure rather than two.

## The three statuses

The target reached reports filled. Something filled, short of the target, reports partial. Nothing filled reports pending.

An average price is worked out only where something has filled, so a pending report carries none.

## What it does not carry

A reason. The report is built from the figures alone, and a change that replaced one resting order with another has nothing to explain: pending here means the replacement is resting, which is the ordinary outcome of a change rather than a failure of one.

## Related

- [The part of a fill a command counts](the-part-of-a-fill-a-command-counts.md)
- [What figures a changed order's replacement is given](what-figures-a-changed-orders-replacement-is-given.md)
- [What an outcome is](what-an-outcome-is.md)
