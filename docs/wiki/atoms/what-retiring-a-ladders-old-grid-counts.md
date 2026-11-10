---
row: P152-02
baseline: 49aa659
created: 2026-11-09 11:51 UTC
modified: 2026-11-09 14:05 UTC
evidence:
  - claim: "Each rung of the old grid is reached by working its name out again from the mode, the command, the rung's place and the old generation"
    source: "`execution_manager.py` 9125, then 9126-9129, then 9130"
  - claim: "A name the account holds no order for is passed over"
    source: "`execution_manager.py` 9131 into 9132"
  - claim: "A rung already in a terminal state has its fills added to both running totals and is taken off the live children"
    source: "`execution_manager.py` 9134, then 9138, then 9139, then 9140, then 9141"
  - claim: "A rung already cancelled marks the amend as having committed its cancel, where a context stands"
    source: "`execution_manager.py` 9135 into 9136"
  - claim: "A rung still working marks that same commitment before anything is sent"
    source: "`execution_manager.py` 9143 into 9144"
  - claim: "Only then is the rung cancelled at the venue, a rung the venue has never heard of passed over in silence"
    source: "`execution_manager.py` 9146-9149, then 9150 into 9151"
  - claim: "Any other venue failure halts the amend in its cancelling phase rather than aborting it"
    source: "`execution_manager.py` 9152 into 9153-9156"
  - claim: "A cancellation is written to the record only where the account's own state holds that rung"
    source: "`execution_manager.py` 9122, then 9123, then 9124, then 9188 into 9189-9195, then 9196, then 9197, then 9199, then 9200, then 9201, both answered with at 9203"
---
# What retiring a ladder's old grid counts

Retiring the grid an amend replaces walks every rung the old generation could have had, and keeps two running totals as it goes.

## Reaching the rungs

Each rung's name is worked out again from the mode, the command, the rung's place and the old generation — [the same working-out](how-a-ladders-rungs-are-found-again.md) a restart uses. A name the account holds no order for is passed over.

## The mark set on both roads

A rung already cancelled marks the amend as having committed its cancel. A rung still working marks that same commitment too — before anything is sent to the venue.

So the commitment is recorded on the strength of what is about to be attempted, rather than on what the venue confirms. Once any rung has been found resting, the amend is committed whether or not that cancel lands.

## What a terminal rung contributes

Its fills, added to both running totals, and its name taken off the live children.

## The cancel and its two failures

The rung is cancelled at the venue. A rung the venue has never heard of is passed over in silence — it was already gone.

Any other venue failure halts the amend in its cancelling phase rather than aborting it, so the watchdog picks it up where it stopped.

## The record of the cancel

Written only where the account's own state holds that rung. A rung absent from the state is cancelled at the venue and left unrecorded here.

## Related

- [How a ladder's rungs are found again](how-a-ladders-rungs-are-found-again.md)
- [How a ladder's prices are changed](how-a-ladders-prices-are-changed.md)
- [What a ladder amend caught mid-flight resumes as](what-a-ladder-amend-caught-mid-flight-resumes-as.md)
