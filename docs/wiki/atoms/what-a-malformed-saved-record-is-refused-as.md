---
row: N63-03
baseline: 49aa659
created: 2026-11-08 19:26 UTC
modified: 2026-11-08 19:26 UTC
evidence:
  - claim: "Each of the three readers wraps its whole build in one catch over five kinds of failure and raises one complaint from any of them"
    source: "`nexus/infrastructure/wal_codec.py` 133 into 153-155, or 650 into 657-659, or 676 into 691-693"
  - claim: "A key that is absent, a value of the wrong kind, a field read off something that has no such field, a figure that will not convert, and a moment that will not parse are the five"
    source: "`nexus/infrastructure/wal_codec.py` 153, naming the five kinds it catches"
  - claim: "The complaint carries the caught failure's own words after a fixed opening, which is all that tells the five apart"
    source: "`nexus/infrastructure/wal_codec.py` 154, and 658, and 692"
  - claim: "Every nested decoder runs inside the outer catch and has none of its own, so a failure deep in a position or a hold is reported as a failure of the whole payload"
    source: "`nexus/infrastructure/wal_codec.py` 137-152, the nested readers at 351-371 and 518-527 raising nothing themselves"
---
# What a malformed saved record is refused as

Reading a record out of [the log](how-a-record-reaches-the-log.md) builds it inside a single catch, and everything that goes wrong inside that build comes back as one complaint.

## One catch over five grounds

Each of the three readers wraps its whole build in a single catch, listing five kinds of failure: a key that is absent, a value of the wrong kind, a field read off something that has no such field, a figure that will not convert, and a moment that will not parse.

Any of the five becomes one complaint, opening with fixed words and carrying the caught failure's own words after them. In the message, that tail is all that separates the five.

The raising keeps the original failure attached as the cause, so a caller that looks past the message can still see which of the five it was.

## How deep it reaches

Every nested reader — a position, a hold, a mode, the capital figures — runs inside that one catch and raises nothing of its own.

So a single unreadable figure inside one position in a snapshot of many is reported as a malformed payload, with nothing naming the position it was in.

[The careful refusal the second event reader makes](the-complaint-folded-into-another.md) is raised inside its own catch, and is taken by it.

[The unpacking, the shape of the payload and its version](the-version-a-saved-record-is-read-at.md) are settled before the build begins, each with a complaint of its own.

## What a caller can tell

From the message: that the build failed, and the tail. From the attached cause: which of the five. Which field and which nested record are in the tail or nowhere.

## Related

- [The version a saved record is read at](the-version-a-saved-record-is-read-at.md)
- [Which version an event is written at](which-version-an-event-is-written-at.md)
- [The complaint folded into another](the-complaint-folded-into-another.md)
