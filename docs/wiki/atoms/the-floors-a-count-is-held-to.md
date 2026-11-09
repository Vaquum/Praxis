---
row: P62-02
baseline: 49aa659
created: 2026-11-08 19:13 UTC
modified: 2026-11-08 19:13 UTC
evidence:
  - claim: "The count of slices is refused below one where a scheme is replanned and refused below nought where one begins, so a scheme may begin with none and may not be replanned to none"
    source: "`events.py` 425-427, against 783-785"
  - claim: "The gap between slices is refused at or below nought on a replan and below nought at the beginning, so a gap of nought is taken at the beginning and refused on a replan"
    source: "`events.py` 429-431, against 787-789"
  - claim: "Both records carry those two fields under the same names, each test naming the field it reads"
    source: "`events.py` 425 and 783 naming the one, 429 and 787 the other"
  - claim: "Neither record asks either count to be a whole number, and the shared check that would is used on other fields in other records"
    source: "`events.py` 425, and 429, and 783, and 787, against the shared check at 1322-1328"
  - claim: "A timeout and the place a scheme has reached are refused below nought, by the same wording as the beginning's counts"
    source: "`events.py` 791-793, and 876-878, and 1567-1569"
---
# The floors a count is held to

Two of [the records](what-every-event-is-held-to.md) carry the same two counts under the same names, and hold them to different floors.

## Slices

A scheme beginning has its count of slices refused below nought. A scheme being replanned has the same count refused below one.

So a scheme may begin saying it has no slices, and may not be replanned to say so. The record of a beginning accepts a figure the record of a replan turns away.

## The gap between them

A scheme beginning has the gap refused below nought, so a gap of nought is taken.

A replan refuses the gap at or below nought, so the same gap of nought is turned away there.

## What neither asks

Neither record asks either count to be a whole number. The floors are compared and nothing else, so a count carrying a fraction is accepted by both.

The shared check that does ask for a whole number is used on other fields in other records, and reaches neither of these.

## The others held the same way

A scheme's timeout, a bracket's timeout, and the place a scheme has reached are each refused below nought, worded as the beginning's counts are.

## So

Whether a count of nought is a fact a record will carry depends on which record is carrying it, and nothing in either names the other.

## Related

- [What every event is held to](what-every-event-is-held-to.md)
- [The two noughts a figure is compared with](the-two-noughts-a-figure-is-compared-with.md)
- [What the shared checks pass over](what-the-shared-checks-pass-over.md)
