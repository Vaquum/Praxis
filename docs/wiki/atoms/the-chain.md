---
row: P2-35
baseline: 49aa659
created: 2026-09-26 08:27 UTC
modified: 2026-09-26 17:41 UTC
evidence:
  - claim: "Each row is given the hash of the one before and its own over its own fields"
    source: "`event_spine.py` 1165-1176"
  - claim: "The first hashed row anchors to a marker the record keeps"
    source: "`event_spine.py` 1195-1198, read at 876"
  - claim: "A record that has lost the marker is refused rather than anchored on a guess"
    source: "`event_spine.py` 879-884"
  - claim: "Rows written before the sealing began carry no hash and are passed over"
    source: "`event_spine.py` 1262-1269"
  - claim: "A tip carrying no hash anchors the next row to the marker too"
    source: "`event_spine.py` 1195-1198"
  - claim: "Altering a marked row needs every marked row after it redone"
    source: "`event_spine.py` 1272-1277, which fails on the next marked row's link"
  - claim: "What the marks fail to catch is set out separately"
    source: "`event_spine.py` 1254-1291, the escapes traced in P2-37"
---
# The chain

Each row in [the event spine](the-event-spine.md) is given two marks: the hash of the row before it, and its own hash taken over its own fields. That links the rows into a **chain**, so that changing what a row says and leaving its marks alone puts the two out of agreement.

The first hashed row anchors to a marker the record keeps for itself. A record that has lost that marker is refused rather than anchored on a guess.

## The rows with no marks

A spine may begin with rows written before the sealing was introduced. Those carry no hash.

They are outside all of it. [The walk](what-the-chain-proves.md) passes over them while they last, and nothing it checks is checked of them. A spine still ending in such a row anchors its next row to the marker, as though starting afresh.

## What the marks are worth

A change to a marked row alone shows up, because the stored mark and the fields beside it stop agreeing.

Altering a marked row with marked rows after it is worse than that for whoever tries it. The next row's backward link then points at a hash that no longer exists, so every marked row after the altered one has to be redone as well, out to the end.

That is the strength of it, and it is narrower than it sounds. [Several kinds of change](what-the-chain-misses.md) go through without a mark being recomputed at all.

## Related

- [What the chain proves](what-the-chain-proves.md)
- [The event spine](the-event-spine.md)
