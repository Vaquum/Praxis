---
row: P88-04
baseline: 49aa659
created: 2026-11-13 21:00 UTC
modified: 2026-11-13 21:00 UTC
evidence:
  - claim: "A projection refuses to be built without an account name"
    source: "`trading_state.py` 149 into 150-151"
  - claim: "It holds a lock for its positions alone, made as it is built"
    source: "`trading_state.py` 161"
  - claim: "A reading of the positions takes that lock and hands back a copy of each one under its own name"
    source: "`trading_state.py` 174 into 175-176"
  - claim: "The two mappings between a parent and its legs are made empty as it is built"
    source: "`trading_state.py` 159, and 160"
  - claim: "A submitted order takes the venue's name for it, is marked open and stamped with the event's moment"
    source: "`trading_state.py` 341, then 342, then 343"
  - claim: "Each leg is mapped to its parent as the order is submitted, and the parent's own list of legs is recorded only where it has any"
    source: "`trading_state.py` 345-346, then 348 into 349"
  - claim: "A scheme already known makes its setting-up a warning, and the event is dropped"
    source: "`trading_state.py` 243 into 244-249"
  - claim: "A scheme not known makes a change of its standing a warning, and that event is dropped too"
    source: "`trading_state.py` 265 into 267-273"
---
# What the projection copies under its lock

The projection holds one lock, and it guards the positions alone.

## What the building asks for

An account name, and nothing else. A projection refuses to be built without one.

It holds a lock for its positions, made as it is built, and the two mappings between a parent and its legs are made empty at the same time.

## Where the leg mappings are filled

A submitted order takes the venue's name for it, is marked open and stamped with the event's moment. Each of its legs is mapped to its parent then, and the parent's own list of legs is recorded only where it has any.

So one mapping gains an entry per leg and the other gains one per parent, and an order with no legs leaves the second untouched.

## The one guarded reading

A reading of the positions takes that lock and hands back a copy of each one under its own name. So a reader holds figures of their own, and the orders and schemes beside them are read with no lock at all.

## The two schemes that are dropped

A scheme already known makes its setting-up a warning, and the event is dropped. A scheme not known makes a change of its standing a warning, and that event is dropped too.

The pair covers both ways a scheme event can disagree with what the projection holds — arriving twice, or arriving for something never set up — and both end the same way: a warning, and nothing changed.

## Related

- [How an event finds its way through the projection](how-an-event-finds-its-way-through-the-projection.md)
- [What a reading of the ledger hands back](what-a-reading-of-the-ledger-hands-back.md)
