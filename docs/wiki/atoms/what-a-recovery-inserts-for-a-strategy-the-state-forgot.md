---
row: N76-01
baseline: 49aa659
created: 2026-11-13 07:30 UTC
modified: 2026-11-13 07:30 UTC
evidence:
  - claim: "Each event the log held is unpacked as the records are walked and gathered into a list"
    source: "`nexus/infrastructure/state_store.py` 268-269, into the list made at 263"
  - claim: "A recovery answers with nothing where neither the snapshot nor any record left a state, and the events gathered on the way go with it"
    source: "`nexus/infrastructure/state_store.py` 274-275, against the state seeded at 260 and replaced at 267"
  - claim: "The signed running figures are derived from the gathered events, and left empty where none were gathered"
    source: "`nexus/infrastructure/state_store.py` 298"
  - claim: "Every strategy named by either those figures or the rolling losses is then looked for in the state's own risk records"
    source: "`nexus/infrastructure/state_store.py` 308"
  - claim: "One the state does not name has an empty risk record put in for it, under its own name"
    source: "`nexus/infrastructure/state_store.py` 309, then 310-312"
  - claim: "A risk record is made outside a recovery where a strategy realizes a figure and has none yet"
    source: "`nexus/infrastructure/praxis_connector/outcome_processor.py` 806, then 808-810"
  - claim: "One is also made where a mark is written for a strategy holding a position and having no record"
    source: "`nexus/core/mtm_loop.py` 297, then 298-300"
  - claim: "The rebuilding that follows the insertion walks the state's own risk records, so a strategy absent from them is never reached"
    source: "`nexus/infrastructure/state_store.py` 314"
---
# What a recovery inserts for a strategy the state forgot

A recovery fills in one thing the state it recovers can be missing: a risk record for a strategy the log has events for.

## What the walk gathers

Each event is unpacked as the records are walked, and gathered into a list made before the walk starts.

## The answer where no state was found

Nothing — where neither the snapshot nor any record of a state change left one. The events gathered on the way go with it, so a log holding events and no state recovers as though it held neither.

## The gap that is filled

Where a state was found, the signed running figures are derived from the gathered events, and left empty where none were gathered.

Every strategy named by either those figures or [the rolling losses](what-a-recovery-takes-before-it-rebuilds.md) is then looked for in the state's own risk records. One the state does not name has an empty risk record put in for it, under its own name.

## Why it is needed

Outside a recovery, a risk record is made in two places: where a strategy realizes a figure and has none yet, and where a mark is written for a strategy holding a position and having no record. Each makes one on the spot.

So a host that wrote an event for a strategy and crashed before writing its next whole state leaves the log holding an event for a strategy the saved state has never heard of.

[The rebuilding that follows](what-a-recovery-writes-at-the-end.md) walks the state's own risk records, and so never reaches a strategy absent from them. Without the insertion that strategy's first figure and first rolling loss are gone — before any later mark or exit could make it a record of its own.

## Related

- [What a recovery takes before it rebuilds](what-a-recovery-takes-before-it-rebuilds.md)
- [What a recovery writes at the end](what-a-recovery-writes-at-the-end.md)
