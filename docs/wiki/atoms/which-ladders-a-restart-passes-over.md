---
row: P173-01
baseline: 49aa659
created: 2026-11-09 13:28 UTC
modified: 2026-11-09 13:28 UTC
evidence:
  - claim: "A command with an ending already recorded is passed over"
    source: "`execution_manager.py` 1313, then 1314 into 1315"
  - claim: "One whose latest state is anything but running is passed over, a state the replay never saw read as running"
    source: "`execution_manager.py` 1317, then 1318, then 1319 into 1320"
  - claim: "A start naming fewer price levels than the least a grid may have is passed over"
    source: "`execution_manager.py` 1322 into 1323"
  - claim: "A start that will not rebuild into a command is passed over"
    source: "`execution_manager.py` 1325, then 1326, then 1327, then 1331"
  - claim: "The deadline is the start's own moment plus the timeout it carried, and there is none where that timeout is nought or less"
    source: "`execution_manager.py` 1333-1337"
  - claim: "The resuming of work fed out on a schedule reads the same replay and refuses on its own terms"
    source: "`execution_manager.py` 1313, against 1895, then 1896 into 1897"
---
# Which ladders a restart passes over

A restart walks every ladder the replay found started, and four readings decide which of them comes back.

## The four

A command with an ending already recorded: passed over. The ending is the last word, and a ladder cannot be resumed past it.

One whose latest state is anything but running: passed over. A state the replay never saw is read as running, so a ladder that only ever started is resumed.

A start naming fewer price levels than the least a grid may have: passed over. A start that will not rebuild into a command: passed over, with the malformed start named.

## The deadline

Worked out from the start's own moment plus the timeout it carried. A timeout of nought or less gives no deadline at all, so such a ladder runs until something else ends it.

## Beside it

[The resuming of work fed out on a schedule](what-stops-a-scheme-being-resumed.md) reads the same replay and refuses on its own terms. The two walks share the gathering and not the readings.

## Related

- [What stops a scheme being resumed](what-stops-a-scheme-being-resumed.md)
- [What a resumed ladder's grid is taken from](what-a-resumed-ladders-grid-is-taken-from.md)
- [How a restart reads its record back](how-a-restart-reads-its-record-back.md)
