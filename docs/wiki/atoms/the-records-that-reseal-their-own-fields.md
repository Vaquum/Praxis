---
row: P62-01
baseline: 49aa659
created: 2026-11-08 19:13 UTC
modified: 2026-11-08 19:13 UTC
evidence:
  - claim: "Seven of the records reseal a run of their own as they are built, eleven fields between them, written by the means that goes round the sealing"
    source: "`events.py` 251-253, or 423, or 763, or 764, or 1155-1157, or 1368, or 1369, or 1413, or 1414, or 1415, or 1562"
  - claim: "The shared check runs before any of that, so the account's name and the moment are weighed first"
    source: "`events.py` 249 ahead of 251, and 418 ahead of 423, and 1366 ahead of 1368"
  - claim: "One of the seven also weighs a name before resealing anything"
    source: "`events.py` 421 ahead of 423"
  - claim: "Resealing a run that is already sealed keeps the very thing handed in, the sealing of an already-sealed run answering with it"
    source: "`events.py` 252, the sealing asked of what was handed in"
  - claim: "Resealing anything else reads it through to build the sealed run, and something that cannot be read through ends the building there"
    source: "`events.py` 252, standing ahead of every test on that field"
  - claim: "The sealing reaches the run and not what the run holds, so an entry that is itself a run stays shared with the caller"
    source: "`events.py` 252, sealing one level"
  - claim: "Three of the seven then put every entry through the shared test for a name, which asks for emptiness alone and so passes a shared entry"
    source: "`events.py` 259-260, and 1164-1165, and 1585-1586, into `_require_str.py` 28-30"
---
# The records that reseal their own fields

Seven of [the forty-two records](what-every-event-is-held-to.md) carry runs of things — eleven fields between them — and reseal each of those runs as they are built.

## What the resealing does

The field is written by the means that goes round the sealing the record otherwise has, which is what lets a sealed record change itself at the moment of its making.

[The shared check](what-every-event-is-held-to.md) runs before any of it, so the account's name and the moment are weighed first. One of the seven weighs a name before resealing too.

## How far the sealing reaches

Handed a list, the record builds a sealed run from it, and adding to that list afterwards leaves the record as it was.

Handed a run already sealed, it keeps the very thing it was given.

Either way the sealing reaches the run and not what the run holds. An entry that is itself a run stays shared with the caller, and the entries that are checked are only asked not to be empty, so a shared entry passes.

## What it costs

Reading a list through is the first reading of that field. Something that cannot be read through ends the building there — not by a refusal, but by the reading — and the complaint names neither the field nor the record.

## The entries

Three of the seven then walk the run and put every entry through [the shared test for a name](the-names-a-record-may-leave-out.md).

## Related

- [What every event is held to](what-every-event-is-held-to.md)
- [The names a record may leave out](the-names-a-record-may-leave-out.md)
