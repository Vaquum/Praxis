---
row: P68-07
baseline: 49aa659
created: 2026-11-13 01:00 UTC
modified: 2026-11-13 01:00 UTC
evidence:
  - claim: "Waiting on the stopped reconnect loop passes over the cancelling alone"
    source: "`binance_ws.py` 275"
  - claim: "A loop that had already ended on a failure of another kind hands that failure out of the waiting"
    source: "`binance_ws.py` 276, with 275 passing over the cancelling alone"
  - claim: "The clearing of the two fields stands after that waiting, so such a failure leaves them holding what they held"
    source: "`binance_ws.py` 282-283, standing after 276"
  - claim: "The sending of the unsubscribe passes over a transport failure and a running out of time, and any other kind escapes"
    source: "`binance_ws.py` 284, naming the two"
  - claim: "The closing of the socket passes over a transport failure, and any other kind escapes"
    source: "`binance_ws.py` 292, naming the one"
  - claim: "Each step stands after the one before, so a failure escaping from any of them leaves the later ones unrun"
    source: "`binance_ws.py` 276, then 282-283, then 284-291, then 292-293"
---
# What a closing can raise

[Closing the venue feed](the-order-closing-the-stream-does-things-in.md) passes over the failures it expects at each step, and each step expects a named kind.

## The loop it waits on

Waiting on the stopped loop passes over the cancelling alone.

A loop that had already ended on a failure of another kind — something unexpected while it was setting a connection up — hands that failure out of the waiting instead.

The closing then raises. The clearing of the two fields stands after the waiting, so they are left holding what they held, and the socket is left open.

So the one failure that leaves the stream in its worst state is one the closing did not cause.

## The two sends

The unsubscribe passes over a transport failure and a running out of time. The closing of the socket passes over a transport failure.

Any other kind escapes from either, and the step after it does not run.

## What that means for a caller

A closing that meets only the expected failures answers, having done all four steps.

A closing that meets anything else raises, and how much of the work was done depends on which step it reached.

## Related

- [The order closing the stream does things in](the-order-closing-the-stream-does-things-in.md)
- [The failures the reconnect loop swallows](the-failures-the-reconnect-loop-swallows.md)
