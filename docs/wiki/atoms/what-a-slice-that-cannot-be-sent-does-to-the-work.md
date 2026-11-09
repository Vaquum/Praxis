---
row: P185-02
baseline: 49aa659
created: 2026-11-09 13:45 UTC
modified: 2026-11-09 13:45 UTC
evidence:
  - claim: "The failure is recorded against the command, naming the order that could not be sent"
    source: "`execution_manager.py` 8278, then 8285-8291, then 8292"
  - claim: "The work is frozen only where no hold stands on it already"
    source: "`execution_manager.py` 8294 into 8295"
  - claim: "Its next run time is forgotten whatever hold it carries"
    source: "`execution_manager.py` 8296"
  - claim: "A partial report then goes out carrying the reason"
    source: "`execution_manager.py` 8298, the reason carried into the report at 8324-8337"
  - claim: "The freezing is what a pass over due work reads to skip it"
    source: "`execution_manager.py` 8295, against 5817-5821"
  - claim: "The same freezing is what a replay rebuilds a frozen command from"
    source: "`execution_manager.py` 8292, against 1225 into 1226"
---
# What a slice that cannot be sent does to the work

A part of [work fed out over time](work-fed-out-over-time.md) that cannot be sent freezes the work and reports what has filled so far, and the command is left for Nexus to decide about.

## What is written

The failure, recorded against the command and naming the order that could not be sent. That record is what a replay rebuilds a frozen command from after a restart.

## What is changed

The work is frozen — but only where no hold stands on it already, so a work already held for protection or draining keeps the hold it has. Its next run time is forgotten whatever hold it carries, which is what stops another part being due.

The freezing is also what a pass over due work reads to skip it.

## What is said

A partial report, carrying the reason the send failed. It leaves the command live: nothing here ends it, and what ends it is a call-off, a change, or its deadline.

## Related

- [Work fed out over time](work-fed-out-over-time.md)
- [What a partial report of a scheme leaves standing](what-a-partial-report-of-a-scheme-leaves-standing.md)
- [What moves a scheme on to its next part](what-moves-a-scheme-on-to-its-next-part.md)
