---
row: P8-03
baseline: 49aa659
created: 2026-11-10 01:30 UTC
modified: 2026-11-10 01:30 UTC
evidence:
  - claim: "A replay clock refuses a start carrying no zone"
    source: "`praxis/replay/replay_clock.py` 29-31"
  - claim: "A start that carries one is kept as it came"
    source: "`praxis/replay/replay_clock.py` 33, reached rather than 31"
  - claim: "A price store asked for no clock of its own uses one answering the current moment in UTC"
    source: "`praxis/arrow_price_store.py` 34-37"
---
# What a clock refuses and what stands in

Two clocks on the Praxis side, one refusing what it is handed and one standing in where nothing was.

## The replay clock

It refuses a start carrying no zone. A start that carries one is kept exactly as it came — no zone is imposed and none is converted, so a clock started in another zone reports in that zone for the rest of the run.

The refusal asks only that a zone be there. It does not ask that the zone be the universal one, where [the records crossing to the other side](the-marker-a-commands-moment-must-carry.md) ask for that marker itself.

## The store's own

A price store asked for no clock uses one answering the current moment in UTC.

So a store left to itself is always on universal time, and a replay clock handed to it need not be.

## Related

- [The replay clock](the-replay-clock.md)
- [The moments with no marker](the-moments-with-no-marker.md)
