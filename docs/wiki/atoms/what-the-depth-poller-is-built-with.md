---
row: P51-01
baseline: 49aa659
created: 2026-11-12 08:30 UTC
modified: 2026-11-12 08:30 UTC
evidence:
  - claim: "The interval between polls and the span a request may take are each refused at or below nought"
    source: "`praxis/binsim/feed.py` 100-101, or 103-104"
  - claim: "The address and the token are each tested for truth alone, so either may be blank space"
    source: "`praxis/binsim/feed.py` 106-107, or 109-110"
  - claim: "The depth floor is asked to be finite and above nought, by calling for its finiteness and comparing it, with nothing asked of its kind"
    source: "`praxis/binsim/feed.py` 112-115"
  - claim: "The count of polls over which an unmoving snapshot counts as stopped must stand at two or more, counting the first poll as one of them"
    source: "`praxis/binsim/feed.py` 117-120 with the floor at 30, counted at 249-252 and read at 256"
  - claim: "Nothing asks that count to be a whole number, so one that is no number by value passes and leaves the counting unable to reach it"
    source: "`praxis/binsim/feed.py` 117 letting it by, read at 256"
  - claim: "The interval is kept as a figure in seconds, and the span as the thing a session reads"
    source: "`praxis/binsim/feed.py` 126-127"
---
# What the depth poller is built with

[The poller fetching depth](binsims-book.md) for the simulated venue checks six of the things it is given, each in a way of its own.

## The two spans

The interval between polls, and the span a single request may take. Each is refused at or below nought, by comparison, with nothing asked of its kind.

The interval arrives in thousandths of a second and is kept as a figure in seconds. The span is kept as the thing a session reads, made once here rather than at each request.

## The two names

The address to fetch from, and the token to fetch with. Each is tested for its truth and nothing more, so either may be blank space alone — [the escape](the-escape-in-the-shared-check-for-a-name.md) this side leaves in several places, here on a token.

## The two figures with floors of their own

The least depth a snapshot must show: asked for its finiteness and compared with nought. Nothing asks its kind, so something answering to those two is kept, and anything else fails at the asking rather than at a check.

The number of polls over which an unmoving snapshot counts as [a feed that stopped](what-a-binsim-snapshot-is-turned-away-for.md): at least two. The first poll counts as one of them, so a floor of two turns a snapshot away on the first repeat.

Nothing asks that count to be a whole number either. One that is no number by value passes, and every comparison the counting makes against it answers false, so the snapshot is kept however long it stands still.

## Related

- [Binsim's book](binsims-book.md)
- [What a binsim snapshot is turned away for](what-a-binsim-snapshot-is-turned-away-for.md)
- [Starting and stopping the depth poller](starting-and-stopping-the-depth-poller.md)
