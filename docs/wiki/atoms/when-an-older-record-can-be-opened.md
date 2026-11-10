---
row: P4-61
baseline: 49aa659
created: 2026-10-16 06:03 UTC
modified: 2026-10-16 06:03 UTC
evidence:
  - claim: "A record written by a newer build is refused outright"
    source: "`praxis/infrastructure/event_spine.py` 494-499"
  - claim: "An older one is brought forward a step at a time, each step conditional on the shape it is at"
    source: "`praxis/infrastructure/event_spine.py` 518-528"
  - claim: "A record with no identity table at all is refused"
    source: "`praxis/infrastructure/event_spine.py` 839-841"
  - claim: "An identity this build did not write, and a missing one, are each refused"
    source: "`praxis/infrastructure/event_spine.py` 849-854 and 856"
  - claim: "A record already at the identity shape has it checked without being brought forward"
    source: "`praxis/infrastructure/event_spine.py` 502-503"
  - claim: "Carrying the old duplicate marks over needs every one of them matched to a fill whose symbol is known"
    source: "`praxis/infrastructure/event_spine.py` 624-633"
  - claim: "More than one symbol in that history is refused as well"
    source: "`praxis/infrastructure/event_spine.py` 635-640"
---
# When an older record can be opened

[A record](the-event-spine.md) written by an earlier build is brought forward to the shape this one expects, a step at a time. A shape from the future, an identity from another build, and duplicate marks that cannot be matched each stop that instead, leaving the host unable to start.

## Written by something newer

A record whose shape is ahead of this build is refused. There is no bringing it backwards: a newer build may have written rows this one cannot read, and guessing at them would be worse than stopping.

## Not this chain

The marks sealing one row to the next are only meaningful against the build that wrote them. So the record carries its own identity, and opening it requires that identity to be the one this build writes. An identity belonging to another build is refused, and so is a record with none recorded, or with no place to record one.

That refusal is the same whether the record is brought forward or already at the shape that keeps an identity: being at the right shape is not being the right record.

## Duplicate marks that cannot be proved

An older record keeps its own list of which fills it has already seen, and bringing that list forward means matching every entry to a fill the record holds.

An entry matching nothing is refused rather than dropped, because dropping it would let that fill be counted a second time. A history holding more than one traded pair is refused too, since a mark from one pair cannot be told from another's.

## Related

- [The event spine](the-event-spine.md)
- [The chain](the-chain.md)
- [Where duplicates stop](where-duplicates-stop.md)

---

Created 2026-10-16 06:03 UTC · Last modified 2026-10-16 06:03 UTC
