---
row: P85-02
baseline: 49aa659
created: 2026-11-09 05:22 UTC
modified: 2026-11-09 05:22 UTC
evidence:
  - claim: "A feed is built holding a stop signal and three counters, every counter starting at nought"
    source: "`feed.py` 133, then 134, and 135, and 136"
  - claim: "The moment of the last good poll is given out as it stands"
    source: "`feed.py` 141"
  - claim: "A feed counts as running where a task exists and has not finished"
    source: "`feed.py` 146"
  - claim: "Between polls the feed waits on the stop signal, with the interval as the longest it will wait"
    source: "`feed.py` 329"
  - claim: "The wait running out is what sends it round for another poll"
    source: "`feed.py` 330-331"
---
# What the feed keeps and what it waits on

A feed is built holding a stop signal and three counters, and it waits on that signal rather than on a clock.

## The counters

Every one starts at nought: the moment of the last good poll, the last-update name the previous poll saw, and how many polls in a row have seen that same name.

The moment of the last good poll is given out as it stands, so a caller can tell how stale the book is without asking the feed anything else.

## What running means

A task exists and has not finished. A feed whose task ended on its own therefore reads as stopped, with the task still held.

## The wait

Between polls the feed waits on the stop signal, with the interval as the longest it will wait. The wait running out is what sends it round for another poll.

So a stop is acted on the moment it is set, rather than at the end of the interval the feed happens to be in. The interval is a ceiling on the wait: the feed sits on the signal for up to that long and leaves the moment it is set.

## Related

- [What the feed demands of a depth payload](what-the-feed-demands-of-a-depth-payload.md)
