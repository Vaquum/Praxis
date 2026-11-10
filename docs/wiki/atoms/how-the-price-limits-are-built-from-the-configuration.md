---
row: N73-03
baseline: 49aa659
created: 2026-11-08 21:33 UTC
modified: 2026-11-08 21:33 UTC
evidence:
  - claim: "A configuration that is not of its own kind is refused before anything is read off it"
    source: "`nexus/core/validator/price_stage.py` 193-195"
  - claim: "The staleness limit is left absent where the configuration's own is absent, and otherwise turned from seconds into milliseconds"
    source: "`nexus/core/validator/price_stage.py` 197, then 198-199"
  - claim: "The two caps and the named source are passed through as they stand"
    source: "`nexus/core/validator/price_stage.py` 203, and 204, and 208"
  - claim: "The per-strategy caps are copied, so the record is built from a copy rather than from the configuration's own mapping"
    source: "`nexus/core/validator/price_stage.py` 205-207"
  - claim: "Everything built is handed to the record, which weighs all five fields as it is made"
    source: "`nexus/core/validator/price_stage.py` 201-209 into 97-179"
  - claim: "The copy of the per-strategy caps reaches the mapping and not what it holds"
    source: "`nexus/core/validator/price_stage.py` 205, copying one level"
---
# How the price limits are built from the configuration

The limits a price is weighed against are made from a host's configuration by one step, which converts one field and passes the rest through.

## What it refuses

A configuration that is not of its own kind, refused before anything is read off it.

## The one conversion

The staleness limit. The configuration carries it in seconds and the record wants milliseconds, so it is multiplied — and left absent where the configuration's own is absent.

So a configuration naming no staleness limit gives a record naming none, and [the check that would use it reads nothing](what-the-price-check-weighs.md).

## What is passed through

The two caps and the named source, as they stand.

## The one copy

The per-strategy caps are copied. The record is built from that copy rather than from the configuration's own mapping, and the copy reaches the mapping and not what it holds.

The record then rebuilds that copy again into [its own sealed form](the-per-strategy-caps-trimmed-and-sealed.md), so the mapping is made twice on the way.

## Where the weighing happens

Not here. Everything built is handed to the record, which weighs all five of its fields as it is made.

So nothing is weighed here, and a figure this step passes through unexamined is weighed by the record it is handed to. Whether such a figure can reach this step at all is settled by what the configuration itself refuses, which is not this module.

## Related

- [What the price records refuse](what-the-price-records-refuse.md)
- [The per-strategy caps, trimmed and sealed](the-per-strategy-caps-trimmed-and-sealed.md)
