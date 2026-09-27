---
row: P2-35
baseline: 49aa659
created: 2026-09-26 08:27 UTC
modified: 2026-09-27 13:46 UTC
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

Each row in [the event spine](the-event-spine.md) stores two codes: one drawn from the row before it, and one drawn from its own contents. That links the rows into a **chain**, so that changing what a row says and leaving its codes alone puts the two out of agreement.

The first row that has a code takes a starting code the spine keeps for itself, in place of the earlier row it has none to draw from. So does a row whose predecessor has no code. A spine that has lost that starting code is refused rather than started from a guess.

## The rows with no codes

A spine may begin with rows written before the stamping was introduced. Those carry no codes.

Those older rows are not checked. [The check](what-the-chain-proves.md) skips them while they last. A spine still ending in such a row takes the starting code for its next row, as though beginning afresh.

## What the codes can reveal

A change to a stamped row alone shows up, because the stored code and the contents beside it stop agreeing.

Altering a stamped row that has stamped rows after it costs more than that. The next row's stored code for the one before it then points at a code that no longer exists, so every stamped row after the altered one has to be redone as well, out to the end.

That is what the codes catch, and it is narrower than it sounds. [Several kinds of change](what-the-chain-misses.md) go through without a code being worked out again at all.

## Related

- [What the chain proves](what-the-chain-proves.md)
- [The event spine](the-event-spine.md)
