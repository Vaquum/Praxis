---
row: P172-01
baseline: 49aa659
created: 2026-11-09 12:53 UTC
modified: 2026-11-09 12:53 UTC
evidence:
  - claim: "Only four kinds of news are considered at all: a fill, a call-off, an expiry and a refusal"
    source: "`execution_manager.py` 10651, then 10652"
  - claim: "The order is looked for among the live orders and then the closed ones"
    source: "`execution_manager.py` 10654, then 10655-10658"
  - claim: "News naming an order the record cannot find makes no report"
    source: "`execution_manager.py` 10659 into 10660"
  - claim: "News whose command has already ended makes none either"
    source: "`execution_manager.py` 10662, then 10663 into 10664"
  - claim: "News whose command belongs to live work fed out over time makes none, that work reporting for itself"
    source: "`execution_manager.py` 10666 into 10667"
  - claim: "News naming an order the command no longer points at makes none"
    source: "`execution_manager.py` 10673 into 10674"
  - claim: "What survives all of it is reported from the admitted totals"
    source: "`execution_manager.py` 10679-10681, then 10683 into 10684"
---
# Which news makes a report

Most of what the venue says about an order makes no report to Nexus, and five readings in a row decide which news does.

## The kind

Only four kinds are considered at all: a fill, [a cancellation](how-a-trade-is-cancelled.md), an expiry and a refusal. Anything else is let past in silence.

## The order

The order is looked for among the live orders, and then among the closed ones. Both sets are searched, and news arriving after its order closed is found among the closed ones. News naming an order neither set holds makes no report.

## The command

News whose command has already ended makes no report. News whose command belongs to live [work fed out over time](work-fed-out-over-time.md) makes none either: that work reports for itself, and a report per child would say the whole command had done what one part of it did.

News naming an order the command no longer points at makes none. A command points at one order at a time, so news about an order a change has superseded stops here.

## What survives

A report built from the admitted totals, with an average price only where something has filled.

## Related

- [What an outcome is](what-an-outcome-is.md)
- [The part of a fill a command counts](the-part-of-a-fill-a-command-counts.md)
- [What status a changed command reports](what-status-a-changed-command-reports.md)
