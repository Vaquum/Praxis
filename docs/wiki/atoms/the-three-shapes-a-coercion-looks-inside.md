---
row: P93-02
baseline: 49aa659
created: 2026-11-09 07:27 UTC
modified: 2026-11-09 07:27 UTC
evidence:
  - claim: "A target naming several kinds has the none-kind dropped and the first of the rest used"
    source: "`event_spine.py` 340-341 into 342, then 343"
  - claim: "A target naming several kinds with nothing but the none-kind left leaves the value alone"
    source: "`event_spine.py` 343, where the list it picks from is empty"
  - claim: "A target naming a sequence turns every item into the first kind the sequence names"
    source: "`event_spine.py` 345-346 into 347-348"
  - claim: "A sequence target naming no kinds, or a value that did not arrive as a list, leaves the value alone"
    source: "`event_spine.py` 347, falling to 349"
  - claim: "A record target has its field kinds read once and kept against that kind"
    source: "`event_spine.py` 358 into 359-360, then 361"
  - claim: "Only the keys the record's fields name are turned and passed on, so any other key is dropped"
    source: "`event_spine.py` 362, then 363"
---
# The three shapes a coercion looks inside

Three kinds of target make the reading look inside the value rather than convert it whole.

## A target naming several kinds

The none-kind is dropped and the first of the rest is used. Where nothing but the none-kind is left, the value is handed back as it came.

So a target naming two real kinds always takes the first, whatever arrived. A value that matches the second is turned into the first, and whether that works depends on the two being close enough that it does.

## A target naming a sequence

Every item is turned into the first kind the sequence names. A sequence target naming no kinds, or a value that did not arrive as a list, leaves the value alone.

So a pair naming two different kinds turns both of its items into the first, and a target expecting a pair of unlike things gets two of the same.

## A target naming a record

Its field kinds are read once and kept against that kind, so the reading of a record's shape happens once however many of them arrive.

Only the keys the record's fields name are turned and passed on. Any other key is dropped in silence — so a stored event carrying a field the record has since lost comes back without it, and nothing says a field was discarded.

## Related

- [How a value is written out and read back](how-a-value-is-written-out-and-read-back.md)
- [How an event is rebuilt from what was stored](how-an-event-is-rebuilt-from-what-was-stored.md)
