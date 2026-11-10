---
row: P85-01
baseline: 49aa659
created: 2026-11-09 05:22 UTC
modified: 2026-11-09 05:22 UTC
evidence:
  - claim: "A poll carries a bearer token in a header of its own, and the answer is read inside the request's own hold"
    source: "`feed.py` 188, then 190, the body read at 205"
  - claim: "The payload must be an object, and so must the part of it the rest is read from"
    source: "`feed.py` 354 into 355, or 359 into 360"
  - claim: "The moment, the last-update name and the two sides are read by key, so a payload missing any of them fails on the key rather than on a message"
    source: "`feed.py` 357, and 362, and 363, and 364-365"
  - claim: "Every price and quantity goes through one check, which raises where the figure will not read as finite and answers the figure where it will"
    source: "`feed.py` 364-365 into 383 into 384, then 386"
  - claim: "Each entry of either side must unpack into exactly a pair"
    source: "`feed.py` 364, and 365"
  - claim: "The four are answered together, and the poll unpacks them in one statement"
    source: "`feed.py` 367, unpacked at 207"
---
# What the feed demands of a depth payload

The feed asks binsim for the book over HTTP, and weighs what comes back before anything reads it.

## The ask

A bearer token in a header of its own. The answer is read inside the request's own hold, so the body is taken before the connection is let go.

## The two shapes

The payload must be an object, and so must the part of it the rest is read from. Each is refused with words saying what arrived instead.

## What is read by key

The moment, the last-update name and the two sides. A payload missing any of them fails on the key itself rather than on a message — so a malformed payload says which key was absent, and a payload of the wrong shape says what shape it had.

## Every figure

Each price and quantity goes through one check, which raises where the figure will not read as finite and answers the figure where it will. Each entry of either side must unpack into exactly a pair, so an entry carrying three things fails as surely as one carrying a letter.

## The answer

The four are answered together, and the poll unpacks them in one statement — the moment, the name, the bids and the asks.

## Related

- [What the feed keeps and what it waits on](what-the-feed-keeps-and-what-it-waits-on.md)
