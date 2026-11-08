---
row: N63-04
baseline: 49aa659
created: 2026-11-12 21:00 UTC
modified: 2026-11-12 21:00 UTC
evidence:
  - claim: "Reading a risk record works out a standing figure from whichever of the two high-water names the payload carries, taking nought where it carries neither"
    source: "`nexus/infrastructure/wal_codec.py` 301"
  - claim: "Each of the two high-water figures then falls back to that standing one, so a payload carrying one of the names comes back with both reading alike"
    source: "`nexus/infrastructure/wal_codec.py` 302, and 303"
  - claim: "The starting capital falls back to the same standing figure, and the equity falls back to the starting capital"
    source: "`nexus/infrastructure/wal_codec.py` 304, and 311"
  - claim: "The figure kept as the realized high water falls back to the equity high water"
    source: "`nexus/infrastructure/wal_codec.py` 313"
  - claim: "So a payload carrying only the equity high water comes back with five figures all reading as that one"
    source: "`nexus/infrastructure/wal_codec.py` 301 into 302, 303, 304, 311 and 313"
  - claim: "Ten more figures fall back to nought, and the run of per-strategy records is required outright"
    source: "`nexus/infrastructure/wal_codec.py` 309, and 310, and 314-321, against 323"
  - claim: "The writer puts all fifteen figures in every payload, so none of these fallbacks can answer a payload this codec wrote"
    source: "`nexus/infrastructure/wal_codec.py` 269-288"
---
# The figures a risk record falls back to

Reading the record of how far down an account is fills in fifteen figures and a run of per-strategy records, and every one of the figures has somewhere to fall back to.

## One figure standing for five

A standing figure is worked out first: whichever of the two high-water names the payload carries, with nought where it carries neither.

Each of the two high-water figures then falls back to that standing one. The starting capital falls back to it as well, the equity falls back to the starting capital, and the figure kept as the realized high water falls back to the equity high water.

So a payload carrying only the equity high water comes back with five figures all reading as that one.

## The rest

Ten more figures fall back to nought: what has been realized, what has not, and the eight measures of how far down the account has been.

The run of per-strategy records has nowhere to fall back to and is required outright, so a payload missing it is [refused](what-a-malformed-saved-record-is-refused-as.md).

## Where any of it can happen

The writer puts all fifteen named figures into every payload it makes.

So none of these fallbacks can answer a payload this codec wrote. They are there for payloads written before a figure was named, and on the ordinary road out and back each figure comes from itself.

## Related

- [What a malformed saved record is refused as](what-a-malformed-saved-record-is-refused-as.md)
- [What a snapshot from an earlier host is read as](what-a-snapshot-from-an-earlier-host-is-read-as.md)
