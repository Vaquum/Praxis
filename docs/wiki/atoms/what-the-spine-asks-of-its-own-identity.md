---
row: P94-02
baseline: 49aa659
created: 2026-11-14 00:30 UTC
modified: 2026-11-14 00:30 UTC
evidence:
  - claim: "A file with no table of its own facts refuses outright, the identity being unverifiable without one"
    source: "`event_spine.py` 839 into 840-841"
  - claim: "Two facts are then weighed in turn, the chain's version and the anchor the first record hangs from"
    source: "`event_spine.py` 843-846, each read at 847"
  - claim: "Either standing absent refuses, saying the chain cannot be attributed to this build"
    source: "`event_spine.py` 849 into 850-854"
  - claim: "Either standing different refuses, saying the chain was written in another dialect"
    source: "`event_spine.py` 856 into 857-861"
  - claim: "The anchor is later read rather than assumed, and its absence refuses again"
    source: "`event_spine.py` 876, then 878 into 879-883, then 885"
  - claim: "Whether a column is already there is answered by asking the table about itself and looking for the name"
    source: "`event_spine.py` 567-568, then 570"
  - claim: "Whether a table is there is answered by one query, a row coming back meaning it is"
    source: "`event_spine.py` 723-724"
  - claim: "A file carrying no version at all reads as nought"
    source: "`event_spine.py` 549-550, then 552"
---
# What the spine asks of its own identity

The spine refuses to open a file whose chain was written under different rules, and it asks two questions to decide.

## The table that must be there

A file with no table of its own facts refuses outright. Without one the identity cannot be verified at all, and the refusal says so.

## The two facts

The chain's version, and the anchor the first record hangs from. Each is weighed in turn, and each can fail two ways.

Standing absent refuses, saying the chain cannot be attributed to this build. Standing different refuses, saying the chain was written in another dialect. The two refusals say different things because they mean different things: one is a file that lost its facts, the other a file that was never this build's.

## Why it is asked at opening

Every record's seal mixes in that version and hangs from that anchor. A file recording others holds a chain this build could neither extend nor check, and no migration can reconcile the two, the records being sealed already.

## The anchor read again

Later, the anchor is read rather than assumed, and its absence refuses again. So the check at opening is not relied on to hold for the rest of the run.

## The three small questions

Whether a column is already there is answered by asking the table about itself and looking for the name. Whether a table is there is answered by one query, a row coming back meaning it is. A file carrying no version at all reads as nought.

## Related

- [What opening the spine does to its schema](what-opening-the-spine-does-to-its-schema.md)
