---
row: P5-02
baseline: 49aa659
created: 2026-11-05 16:22 UTC
modified: 2026-11-06 06:59 UTC
evidence:
  - claim: "The record saying the receiver took a report is built, handed to the Praxis loop and waited on for up to ten seconds"
    source: "`praxis/launcher.py` 3155-3159 and 3164-3166 before the wait at 3167"
  - claim: "A wait that runs out is passed over, and the catch calls off nothing of what was handed over"
    source: "`praxis/launcher.py` the catch at 3168, which calls off nothing of what 3164-3166 handed over"
  - claim: "Where the loop or the trading side is absent that record is not built at all"
    source: "`praxis/launcher.py` 3148-3153, which returns rather than reaching 3155-3167"
  - claim: "The record saying Praxis stopped trying has that same absent-loop road"
    source: "`praxis/launcher.py` 3190-3195, which returns rather than reaching 3197-3210"
---
# What can stop a closing record going down

The record saying a receiver took a report is written on a road that hands the write to the Praxis loop and waits up to ten seconds for word back.

## The wait that runs out

Where that wait runs out the failure is passed over, and nothing calls the handed-over write off, so the record may still land afterwards.

## The road that builds nothing

Where the loop or the trading side is not there, the road returns before the record is built. [The record saying Praxis stopped trying](outcomes-that-never-come-back.md) has that same road, so either can end with no record even attempted.

## Related

- [Outcomes that never come back](outcomes-that-never-come-back.md)
- [How an undelivered outcome is replayed](how-an-undelivered-outcome-is-replayed.md)
