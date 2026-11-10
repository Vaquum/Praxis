---
row: P68-06
baseline: 49aa659
created: 2026-11-08 20:40 UTC
modified: 2026-11-08 20:40 UTC
evidence:
  - claim: "Setting up begins by closing any socket it already holds, with a transport failure of that closing passed over and a failure of any other kind escaping"
    source: "`binance_ws.py` 153, naming the one kind it passes over"
  - claim: "It then clears the socket it holds and the subscription's name, whether or not there was a socket to close"
    source: "`binance_ws.py` 155, and 156"
  - claim: "That tearing down stands before the address is weighed, so a refused address leaves the stream holding nothing where the closing went through"
    source: "`binance_ws.py` 152-156 ahead of 170-172"
  - claim: "The new socket is put in place only once the subscribing has returned"
    source: "`binance_ws.py` 186, standing after 180"
  - claim: "So between the clearing and that moment the stream holds nothing, and the two readings it offers answer with nothing"
    source: "`binance_ws.py` 155-156 until 186, read at 101 and 110"
  - claim: "The fields are still as they were while the old socket's closing is waited on, the clearing standing after it"
    source: "`binance_ws.py` 154 ahead of 155"
---
# What setting up tears down first

Setting [the venue feed](the-venue-feed.md) up is written to be safe to call over an existing connection, and the first thing it does is let that connection go.

## The old socket

Any socket already held is closed, and a transport failure of that closing is passed over. A connection already broken therefore costs nothing to let go of.

A failure of another kind escapes instead, and the clearing below never runs — so the stream is left holding the socket it was trying to be rid of.

The socket and the subscription's name are cleared after that closing has been waited on, whether or not there was a socket to close. While it is being waited on the two fields still hold what they held.

## Before the address is weighed

That tearing down stands ahead of the check on the address.

So a stream asked to set up again with an address it refuses ends holding nothing, having let go of what it had. The refusal is about the address; the cost is the connection.

## The gap in the middle

The new socket is put in place only once the subscribing has returned.

Between the tearing down and that moment the stream holds nothing, and the two readings it offers — for the socket and for the subscription — answer with nothing to match.

A caller reading either during a setting up therefore sees an unconnected stream. An opening asked for in that gap is a separate matter: it has a second reason to answer at once, the reconnect loop still running, and takes it whatever the socket field says.

## Related

- [What opening the stream does and does not do](what-opening-the-stream-does-and-does-not-do.md)
- [The address the stream will accept](the-address-the-stream-will-accept.md)
- [The venue feed](the-venue-feed.md)
