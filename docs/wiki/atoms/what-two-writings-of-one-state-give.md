---
row: N63-10
baseline: 49aa659
created: 2026-11-12 22:00 UTC
modified: 2026-11-12 22:00 UTC
evidence:
  - claim: "The two sets of handled names are put into order as they are written"
    source: "`nexus/infrastructure/wal_codec.py` 94, and 95"
  - claim: "They are read back as sets, so the order goes no further than the bytes"
    source: "`nexus/infrastructure/wal_codec.py` 150, and 151"
  - claim: "Every mapping is written in the order it is held in, nothing ordering what it walks"
    source: "`nexus/infrastructure/wal_codec.py` 85, or 91, or 93, or 181, or 286"
  - claim: "So two states holding the same things in a different order give different bytes"
    source: "`nexus/infrastructure/wal_codec.py` 85, walking the mapping as it stands"
---
# What two writings of one state give

Writing the same state twice gives the same bytes for two of its fields and not for the rest.

## The two that are ordered

The two sets of names already handled are put into order as they are written. Those two fields therefore come out the same way whatever order the state kept them in.

They are read back as sets, so that order goes no further than the bytes. It is there for the writing and nothing else reads it.

## The rest

Every mapping — the positions, the per-strategy modes, the dust, the per-strategy money and the per-strategy risk — is written in the order it is held in. Nothing orders any of them.

## What follows

Two states holding the same positions under the same names give different bytes where those names were added in a different order.

So the bytes are not a fingerprint of the state. Two of them matching tells you the two states were written from the same ordering as well as the same contents, and two differing tells you nothing about whether the states differ.

## Related

- [The copies taken before a record is written](the-copies-taken-before-a-record-is-written.md)
- [What a malformed saved record is refused as](what-a-malformed-saved-record-is-refused-as.md)
