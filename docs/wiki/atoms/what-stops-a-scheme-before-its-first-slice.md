---
row: P170-01
baseline: 49aa659
created: 2026-11-16 05:30 UTC
modified: 2026-11-16 05:30 UTC
evidence:
  - claim: "The count of parts and the gap between them are read from the settings first"
    source: "`execution_manager.py` 5712"
  - claim: "A call-off already standing against the command is taken off the waiting list and ends the scheme as cancelled with nothing filled"
    source: "`execution_manager.py` 5713, then 5715, then 5720-5729, then 5730"
  - claim: "The venue's lot step is used where the venue's sizes are held, and nothing stands in for it otherwise"
    source: "`execution_manager.py` 5733, then 5734"
  - claim: "A planning that refuses ends the scheme as rejected, carrying the refusal's own words as the reason"
    source: "`execution_manager.py` 5736, then 5737-5739, then 5740, then 5746-5755, the reason built at 5754, then 5756"
  - claim: "Otherwise the start is recorded and applied"
    source: "`execution_manager.py` 5758-5775, then 5776, then 5777"
  - claim: "The count recorded is the number of parts actually planned, where both refusals report the number asked for"
    source: "`execution_manager.py` 5767, against 5727, or 5753"
---
# What stops a scheme before its first slice

Starting [work fed out over time](work-fed-out-over-time.md) can end before any part of it is sent, and the two ways it ends report different statuses.

## Read before anything is decided

The count of parts and the gap between them, from the settings.

## Called off already

A call-off standing against the command is taken off the waiting list, and the scheme ends as cancelled with nothing filled. The call-off arrived before the work began, and taking it off the list is what keeps it from being applied twice.

## Refused by the planning

The venue's lot step is used where the venue's sizes are held, and nothing stands in for it otherwise — so a host without those sizes plans parts that are not snapped to the venue's steps.

A planning that refuses ends the scheme as rejected, carrying the refusal's own words as the reason, so what the planning objected to reaches Nexus.

## What the count means in each case

The start, once recorded, names the number of parts actually planned. Both refusals report the number asked for instead — there are no planned parts to count, and the figure that reaches Nexus is the one the settings asked for.

## Related

- [Work fed out over time](work-fed-out-over-time.md)
- [What a partial report of a scheme leaves standing](what-a-partial-report-of-a-scheme-leaves-standing.md)
- [What ending a scheme forgets](what-ending-a-scheme-forgets.md)
