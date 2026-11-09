---
row: P93-03
baseline: 49aa659
created: 2026-11-14 00:00 UTC
modified: 2026-11-14 00:00 UTC
evidence:
  - claim: "An event's kind is looked up by the name stored beside it, and a name the registry does not hold raises"
    source: "`event_spine.py` 381 into 382-384"
  - claim: "The payload is parsed before any field is looked at"
    source: "`event_spine.py` 385"
  - claim: "The kind's field kinds are read from a map built ahead of time"
    source: "`event_spine.py` 386"
  - claim: "A nested record's are kept the first time one of that kind is seen instead"
    source: "`event_spine.py` 359-360"
  - claim: "Only the keys those fields name are turned, and the event is built from them alone"
    source: "`event_spine.py` 387, then 388"
---
# How an event is rebuilt from what was stored

An event comes back from the spine as a name and a payload, and the name decides what the payload becomes.

## The name

Looked up in the registry of kinds. A name the registry does not hold raises, so a stored event of a kind the code no longer has stops the reading rather than being skipped over.

## The payload

Parsed before any field is looked at, so a payload that will not parse fails before the kind's fields matter.

## Where the field kinds come from

A map built ahead of time. [A nested record's](the-three-shapes-a-coercion-looks-inside.md) are kept the first time one of that kind is seen instead — so the top level pays its cost once at startup, and a nested kind pays it on the first event that carries one.

## What is built

Only the keys those fields name are turned, and the event is built from them alone.

So an event stored while a field existed comes back without that field once the code has dropped it, and nothing records that something was discarded. The reading cannot tell a field that was never written from one that is no longer wanted.

## Related

- [The three shapes a coercion looks inside](the-three-shapes-a-coercion-looks-inside.md)
- [How a value is written out and read back](how-a-value-is-written-out-and-read-back.md)
