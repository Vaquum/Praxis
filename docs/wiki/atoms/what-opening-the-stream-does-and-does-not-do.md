---
row: P68-01
baseline: 49aa659
created: 2026-11-08 20:40 UTC
modified: 2026-11-08 20:40 UTC
evidence:
  - claim: "Opening the stream answers at once where a socket is already open, and again where a reconnect loop is already running"
    source: "`binance_ws.py` 128-129, then 130-131"
  - claim: "So two openings in a row do nothing the second time, and neither is refused"
    source: "`binance_ws.py` 128-131, each answering rather than raising"
  - claim: "The reconnect loop is started only where a handler for arriving messages has been set"
    source: "`binance_ws.py` 134-135"
  - claim: "A stream with no such handler therefore connects and subscribes and never reconnects"
    source: "`binance_ws.py` 133 without 135"
  - claim: "The setting up runs before the loop is started, so a failure to connect or subscribe leaves no loop behind"
    source: "`binance_ws.py` 133 ahead of 135"
  - claim: "The loop reads frames through a step that asserts both the socket and the handler are there"
    source: "`binance_ws.py` 396, and 397"
  - claim: "Entering the stream as a context opens it and leaving closes it, whatever the body did"
    source: "`binance_ws.py` 301-302, and 315"
  - claim: "The socket and the subscription's name are offered for reading, each answering with nothing where none is held"
    source: "`binance_ws.py` 101, and 110"
---
# What opening the stream does and does not do

Opening [the venue feed](the-venue-feed.md) either sets one up or finds one already there.

## Two ways of doing nothing

Where a socket is already open, the opening answers at once. Where a reconnect loop is already running, the same.

Neither is refused. So asking twice is harmless, and a caller cannot tell from the answer whether it got a new connection or found an old one.

## The loop that may not be started

The reconnect loop is started only where a handler for arriving messages has been set.

A stream with no handler therefore connects, subscribes, and never reconnects. A disconnection leaves it closed with nothing watching, and the next opening is what notices.

## The order of the two steps

The setting up runs first and the loop is started only after it has returned.

So a failure to connect, or a subscription the venue refuses, leaves no loop behind — the failure travels to the caller and nothing is left running.

[What setting up tears down first](what-setting-up-tears-down-first.md) is whatever the stream was already holding.

## What the loop assumes

Reading frames begins by asserting both the socket and the handler are there. Neither is checked, because the only road to the loop has already set both.

## As a context

Entering the stream as a context opens it; leaving closes it, whatever the body did.

## Related

- [The venue feed](the-venue-feed.md)
- [The address the stream will accept](the-address-the-stream-will-accept.md)
- [What setting up tears down first](what-setting-up-tears-down-first.md)
