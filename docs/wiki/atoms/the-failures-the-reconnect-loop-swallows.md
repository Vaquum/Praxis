---
row: P68-05
baseline: 49aa659
created: 2026-11-13 01:00 UTC
modified: 2026-11-13 01:00 UTC
evidence:
  - claim: "A failure of the reading of the ordinary kind is logged and the loop carries on into its waiting, whatever that failure was"
    source: "`binance_ws.py` 336-339"
  - claim: "That catch names the ordinary kind of failure, and a cancelling is of another kind, so a cancelling ends the loop instead"
    source: "`binance_ws.py` 338, naming the ordinary kind alone"
  - claim: "The cancelling a closing causes therefore reaches the loop's end rather than its waiting"
    source: "`binance_ws.py` 274 into 338, which does not catch it"
  - claim: "A failed attempt to set up again is caught by the three kinds named and the waiting goes round, so only those three keep the loop alive"
    source: "`binance_ws.py` 358-363"
  - claim: "A failure of another kind during the setting up leaves the loop altogether"
    source: "`binance_ws.py` 358, naming three kinds"
  - claim: "Each of the two callbacks is run inside a catch of its own naming the ordinary kind, so an ordinary failure of either is logged and the loop goes on"
    source: "`binance_ws.py` 384, naming the ordinary kind"
  - claim: "A callback that is not set is passed over without being called"
    source: "`binance_ws.py` 379-380"
---
# The failures the reconnect loop swallows

[The loop that keeps the venue feed up](the-venue-feed.md) is written to survive almost anything, and what it does not survive is worth knowing.

## The reading

A failure of the reading of the ordinary kind is logged and the loop carries on into its waiting, whatever that failure was. That is deliberate: a transport failure surfacing from the frames must not end the loop.

But the catch names the ordinary kind of failure, and a cancelling is of another kind altogether.

So the cancelling a closing causes is not swallowed. It reaches the end of the loop and the loop stops, which is how closing the stream actually stops it.

## The setting up again

A failed attempt to set up again is caught where the failure is one of three named kinds — the venue refusing, a transport failure, or running out of time — and the waiting goes round with the count raised.

A failure of another kind during the setting up is not caught. It leaves the loop altogether, and the loop is not running after it.

So the loop survives the venue being unreachable indefinitely, and does not survive something unexpected in the setting up.

## The two callbacks

The one for a disconnection and the one for a reconnection are each run inside a catch of their own, naming the ordinary kind. An ordinary failure of either is logged and the loop goes on, so a caller's own mistake cannot stop the reconnecting.

A callback failing in a way outside that kind ends the loop, as such a failure does everywhere else here.

A callback that was never set is passed over without being called at all.

## Related

- [The venue feed](the-venue-feed.md)
- [The order closing the stream does things in](the-order-closing-the-stream-does-things-in.md)
