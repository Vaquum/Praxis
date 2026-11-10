---
row: P162-02
baseline: 49aa659
created: 2026-11-09 12:31 UTC
modified: 2026-11-09 14:05 UTC
evidence:
  - claim: "The figures reported are the admitted totals kept for the command"
    source: "`execution_manager.py` 8314, then 8316-8318"
  - claim: "An average price is worked out only where something has filled, and left absent otherwise"
    source: "`execution_manager.py` 8320 into 8321-8322"
  - claim: "The count of slices reported is the scheme's own place in its plan"
    source: "`execution_manager.py` 8324-8337, the count named at 8332, and 8333"
  - claim: "One moment is taken and carried into both the report and the record of it"
    source: "`execution_manager.py` 8315, then 8335, then 8341"
  - claim: "The record goes down and is applied, and the report is then handed out with retries"
    source: "`execution_manager.py` 8350, then 8351, then 8353"
  - claim: "The terminal report of the same scheme marks the command ended and drops it from the live commands and from the aborted ones"
    source: "`execution_manager.py` 8426, then 8427, then 8428, against 8339"
  - claim: "The terminal report may also record the trade closed where the fill closes the position"
    source: "`execution_manager.py` 8430 into 8433-8440"
---
# What a partial report of a scheme leaves standing

A partial report tells Nexus how much of a [scheme](work-fed-out-over-time.md) has filled while the scheme is still running, and it is the one report that changes nothing about the command it names.

## What it reports

The figures are the admitted totals kept for the command — what its slices' fills were allowed to count, not what the venue filled. An average price is worked out only where something has filled, and left absent otherwise.

The count of slices reported is the scheme's own place in its plan: how far the cursor has moved, against how many were planned.

One moment is taken at the start and carried into both the report and the record of it, so the two cannot disagree about when.

## What it does not touch

The terminal report of the same scheme marks the command ended, drops it from the live commands and from the aborted ones, and where the fill closes the position records the trade closed. The partial report does none of those: it writes the record of the report, applies it, and hands the report out with retries.

So a scheme can report over and over as it fills, and each report leaves the command exactly as live as it found it.

## Related

- [Work fed out over time](work-fed-out-over-time.md)
- [What an outcome is](what-an-outcome-is.md)
- [The part of a fill a command counts](the-part-of-a-fill-a-command-counts.md)
