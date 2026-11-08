---
row: N63-09
baseline: 49aa659
created: 2026-11-12 22:00 UTC
modified: 2026-11-12 22:00 UTC
evidence:
  - claim: "The second event reader writes a careful complaint for an outcome name that is not text, that is empty, or that holds only spaces, and that complaint carries what arrived"
    source: "`nexus/infrastructure/wal_codec.py` 678-683"
  - claim: "It is raised inside the catch the same reader opened, and that catch answers the kind it was raised as"
    source: "`nexus/infrastructure/wal_codec.py` 683 standing inside 676, caught at 691"
  - claim: "So what reaches a caller is the fixed opening with the careful words folded into its tail"
    source: "`nexus/infrastructure/wal_codec.py` 692"
  - claim: "A name absent altogether never reaches the careful complaint, the reading of the key failing first"
    source: "`nexus/infrastructure/wal_codec.py` 677 ahead of 678"
---
# The complaint folded into another

The reader for the second event version writes a careful complaint about a bad outcome name, and the catch around it takes that complaint for a failure.

## What the careful complaint says

A name that is not text, that is empty, or that holds only spaces is refused, and the complaint carries what arrived so a reader can see it.

## Why it is never seen as written

It is raised inside the catch the same reader opened, and the catch answers the kind it was raised as. So it is caught, and what reaches the caller is the fixed opening for [a malformed payload](what-a-malformed-saved-record-is-refused-as.md) with the careful words folded into its tail.

The words survive. What is lost is the difference between a complaint written for this case and one assembled from whatever failed.

## The case it never answers

A name absent altogether fails on the reading of the key, which comes first. That failure is caught by the same catch, so an absent name and a blank one come back alike — and the careful complaint, written to show a reader the value that arrived, runs only where a value did arrive.

## Related

- [What a malformed saved record is refused as](what-a-malformed-saved-record-is-refused-as.md)
- [Which version an event is written at](which-version-an-event-is-written-at.md)
