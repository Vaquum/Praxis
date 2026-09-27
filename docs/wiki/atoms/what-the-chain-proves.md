---
row: P2-36
baseline: 49aa659
created: 2026-09-25 20:44 UTC
modified: 2026-09-27 13:51 UTC
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

Praxis can be asked to check [the chain](the-chain.md) from end to end and say whether every row that has codes still matches its contents and the row before it.

It reads the starting code the spine keeps before it looks at any row. A spine that has lost that code stops the check there, naming no row: nothing has been examined, so nothing can be blamed.

## What stops the check

Past that, three things about a row stop it.

A row with no code appearing after a stamped one stops it, because the stamping cannot begin again part way along. A row whose backward code does not match the row before it stops it. And a row whose own code does not come out the same when worked out again from its contents stops it.

It stops at the first row it refuses, so what it reports is the first row whose codes do not match. Rows past that point go unexamined, and a second fault further on stays hidden until the first is dealt with.

## What a refusal does not say

Each refusal names the check that failed, and more than one cause reaches each check.

A backward code that does not match can mean a row was taken out, or that the code itself was altered. A row's own code that does not come out the same can mean the contents were changed, or that the stored code was.

The check says where the codes stopped matching. Telling which of those happened, and who did it, takes separate work — and [a thorough enough rewrite, or a chain simply cut short](the-chain.md), leaves nothing here to find.

## Related

- [The chain](the-chain.md)
- [The event spine](the-event-spine.md)
