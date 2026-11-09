---
row: P97-01
baseline: 49aa659
created: 2026-11-14 02:00 UTC
modified: 2026-11-14 02:00 UTC
evidence:
  - claim: "A fill takes a road of its own, chosen by the kind of event it is"
    source: "`event_spine.py` 991"
  - claim: "A money movement takes a second such road, on the same shape"
    source: "`event_spine.py` 1072, into 1074-1077 into 1078, then 1079"
  - claim: "Its guards are the same pair, each rolling back and raising on"
    source: "`event_spine.py` 1073 into 1080 into 1081 then 1090, and 1091-1092 into 1093 into 1094 then 1103"
  - claim: "Its deduplication row is inserted first, and whether that insert changed anything is what marks it a repeat"
    source: "`event_spine.py` 1018-1021 into 1022"
  - claim: "The event is appended only where the insert was not a repeat, so a repeat appends nothing"
    source: "`event_spine.py` 1023"
  - claim: "Both the insert and the append stand under one guard, which rolls back and raises on"
    source: "`event_spine.py` 1017 into 1024 into 1025, then 1035"
  - claim: "The commit on that road rolls back and raises on by itself, rather than through the routine that does the same"
    source: "`event_spine.py` 1036-1037 into 1038 into 1039, then 1049, against 921-922 into 923 then 924 then 926"
  - claim: "The ordinary road appends and then commits through that routine"
    source: "`event_spine.py` 1125, then 1126"
  - claim: "Either road answers the sequence it was given, or nothing where a repeat was dropped"
    source: "`event_spine.py` 1070, or 1123, or 1136, against 1050, or 1104"
---
# What an append does in one transaction

An append puts an event in the spine's file and seals it, and a fill does more than the others under one transaction.

## The road a fill takes

Chosen by the kind of event it is. Its deduplication row is inserted first, and whether that insert changed anything is what marks the fill a repeat.

The event is appended only where the insert was not a repeat. So a repeat inserts nothing and appends nothing, and the two facts cannot disagree — they are the same insert.

## The guards on that road

Both the insert and the append stand under one guard, which rolls back and raises on. The commit then stands under a second guard that rolls back and raises on by itself, rather than through the routine written to do exactly that.

So the fill road reimplements the closing the ordinary road calls. The behaviour matches; the code does not share.

## The second such road

A money movement takes one too, on the same shape: a deduplication row keyed on its own identifier, an append only where that insert was not a repeat, and the same pair of guards.

So two kinds of event are deduplicated in the file itself, each against a different identifier, and both reimplement the closing.

## The ordinary road

Appends and then commits through that routine.

## What either answers

The sequence it was given, or nothing where a repeat was dropped. A caller reading nothing back therefore learns that the event was already in the file, and cannot tell that from an event it never sent.

## Related

- [How the spine closes a write](how-the-spine-closes-a-write.md)
- [What sealing an appended event takes](what-sealing-an-appended-event-takes.md)
