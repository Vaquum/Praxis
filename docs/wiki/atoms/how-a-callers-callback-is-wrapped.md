---
row: P98-02
baseline: 49aa659
created: 2026-11-14 02:30 UTC
modified: 2026-11-14 02:30 UTC
evidence:
  - claim: "The shared wrapper answers at once for a callback that is absent, so what it hands back can always be awaited"
    source: "`praxis/trading.py` 143-144 into 145, handed back at 152"
  - claim: "Otherwise it calls the callback and awaits the answer only where the answer can be awaited"
    source: "`praxis/trading.py` 147, then 149 into 150"
  - claim: "One setter does not use that wrapper for an absent callback, passing the absence straight on instead"
    source: "`praxis/trading.py` 407 into 408, then 409"
  - claim: "For a real callback that setter builds an adapter of its own, on the same shape as the shared one"
    source: "`praxis/trading.py` 411, then 413-417, handed on at 419"
---
# How a caller's callback is wrapped

A callback handed to the facade is wrapped so that whoever calls it can always await it, and one setter is deliberately left out of that.

## The shared wrapper

For a callback that is absent, it answers at once and does nothing. So what it hands back can always be awaited, whether a caller supplied anything or not.

Otherwise it calls the callback and awaits the answer only where the answer can be awaited. A plain callback and one that must be awaited therefore both work, and the wrapper decides which by looking at what came back rather than at what was passed in.

## The setter that opts out

One does not use that wrapper for an absent callback. It passes the absence straight on instead.

The reason is what the far side makes of it: an absent callback there means nobody is listening, and a wrapper that does nothing would say somebody is. So the absence has to survive, and only this setter has a far side that reads it.

## What that setter does instead

For a real callback it builds an adapter of its own, on the same shape as the shared one: call, and await the answer where the answer can be awaited.

So the shape exists twice in the file — once shared, once written out — and the duplication is what lets the absence through on the one road that needs it.

## Related

- [What the facade refuses once a start has begun](what-the-facade-refuses-once-a-start-has-begun.md)
