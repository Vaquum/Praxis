---
row: N63-05
baseline: 49aa659
created: 2026-11-12 21:00 UTC
modified: 2026-11-12 21:00 UTC
evidence:
  - claim: "A snapshot with no health mode in it is read as the running mode, while the account's own mode and its holds are read from their own fields"
    source: "`nexus/infrastructure/wal_codec.py` 142 into 502-503, the mode read at 141 and the holds at 143"
  - claim: "A snapshot with no block of halting holds is read as a block with none of them standing, and the same for the block of reduce-only holds"
    source: "`nexus/infrastructure/wal_codec.py` 143 into 438-439, and 144 into 473-474"
  - claim: "Within a block that is there, three of the six holds are required and three fall back to a hold that is not standing"
    source: "`nexus/infrastructure/wal_codec.py` 446-448, against 449-457"
  - claim: "A per-strategy risk record missing its unrealized figure reads it as nought"
    source: "`nexus/infrastructure/wal_codec.py` 253"
  - claim: "The dust, the outcome names already handled and the dust-close names already handled each fall back to nothing at all"
    source: "`nexus/infrastructure/wal_codec.py` 134, and 150, and 151"
  - claim: "The capital, the risk record, the positions, the mode and the per-strategy modes have nowhere to fall back to and are required outright"
    source: "`nexus/infrastructure/wal_codec.py` 138, and 139, and 140, and 141, and 147"
  - claim: "The writer puts every one of those fields into every snapshot it makes"
    source: "`nexus/infrastructure/wal_codec.py` 81-96"
---
# What a snapshot from an earlier host is read as

A saved snapshot gained fields over time, and [reading one](the-version-a-saved-record-is-read-at.md) fills in whatever an older writer left out.

## The mode that is assumed

A snapshot with no health mode in it is read as the running mode.

The account's own mode and its holds come from their own fields, so what the host does on coming back up is settled by those rather than by this one. What the default decides is that the health side is read as having found nothing wrong, and nothing in the reading says the figure was absent at all.

## The holds

A snapshot with no block of halting holds is read as a block with none of them standing, and a snapshot with no block of reduce-only holds the same.

Within a block that is there, three of the six holds are required and three fall back to a hold that is not standing. So a block written before the newer three existed reads them as clear, and a block missing any of the original three is [refused](what-a-malformed-saved-record-is-refused-as.md).

## The smaller ones

A per-strategy risk record missing its unrealized figure reads it as nought. The dust, the outcome names already handled, and the dust-close names already handled each fall back to nothing at all.

## What is required

The capital, the risk record, the positions, the mode and the per-strategy modes.

## Where any of it can happen

The writer puts every one of these fields into every snapshot it makes, so on the road out and back nothing falls back. Each of these answers a snapshot written by an earlier host — and the first of them answers it by assuming the account was running.

## Related

- [The version a saved record is read at](the-version-a-saved-record-is-read-at.md)
- [The figures a risk record falls back to](the-figures-a-risk-record-falls-back-to.md)
