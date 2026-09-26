---
row: P2-36
baseline: 49aa659
created: 2026-09-25 20:44 UTC
modified: 2026-09-26 17:41 UTC
evidence:
  - claim: "The walk reads the marker before any row, and stops there if it is gone"
    source: "`event_spine.py` 1254, refused at 879-884"
  - claim: "An unhashed row after a hashed one is refused"
    source: "`event_spine.py` 1263-1268"
  - claim: "A backward link that does not match is refused"
    source: "`event_spine.py` 1272-1277"
  - claim: "A hash that does not come out the same is refused"
    source: "`event_spine.py` 1279-1287"
  - claim: "It stops at the first row it refuses"
    source: "either `event_spine.py` 1277 or 1287, whichever check fails first"
  - claim: "The marks are worked out afresh from the fields beside them"
    source: "`event_spine.py` 1279-1283, the working-out at 419-434"
---
# What the chain proves

Praxis can be asked to walk [the chain](the-chain.md) from end to end and say whether it still agrees with itself.

It reads the marker the record keeps before it looks at any row. A record that has lost the marker stops the walk there, with no row named — nothing has been examined yet, so nothing can be blamed.

## The three refusals

Past that, three things about a row stop the walk.

An unhashed row appearing after a hashed one stops it, because the sealing cannot begin again part way along. A row whose backward link does not match the row before it stops it. And a row whose hash does not come out the same when worked out afresh from its own fields stops it.

It stops at the first row it refuses, so what it reports is where the chain first stopped agreeing. Rows past that point go unexamined, and a second fault further on is not found until the first is dealt with.

## What a refusal does not say

Each refusal names the check that failed, and more than one cause reaches each check.

A link that does not match can mean a row was taken out, or that the link itself was altered. A hash that does not come out the same can mean the contents were changed, or that the stored hash was.

The walk says where the chain stopped agreeing. Which of those happened, and who did it, is a separate job — and [a rewrite thorough enough, or a chain simply cut short](the-chain.md), leaves nothing here to find.

## Related

- [The chain](the-chain.md)
- [The event spine](the-event-spine.md)
