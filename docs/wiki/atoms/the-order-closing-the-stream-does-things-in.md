---
row: P68-04
baseline: 49aa659
created: 2026-11-13 01:00 UTC
modified: 2026-11-13 01:00 UTC
evidence:
  - claim: "Closing stops the reconnect loop first, waiting for it and passing over the cancelling it caused"
    source: "`binance_ws.py` 273-277"
  - claim: "The socket and the subscription's name are then taken into local names and the fields cleared, before anything is sent"
    source: "`binance_ws.py` 280-283"
  - claim: "An opening asked for once the fields are cleared sets up afresh rather than being handed the socket being closed"
    source: "`binance_ws.py` 282-283, read by the opening at 128"
  - claim: "An unsubscribe is then sent on the local socket, with a transport failure or a running out of time passed over and any other kind escaping"
    source: "`binance_ws.py` 284, naming the two"
  - claim: "That request names the subscription only where one was recorded, and is sent without it otherwise"
    source: "`binance_ws.py` 289-290"
  - claim: "The socket is closed last, with a transport failure of that closing passed over and any other kind escaping"
    source: "`binance_ws.py` 292, naming the one kind"
---
# The order closing the stream does things in

Closing [the venue feed](the-venue-feed.md) does four things in a fixed order, and tells the caller about none of them.

## The loop first

The reconnect loop is stopped, waited for, and the cancelling it caused is passed over. So the closing does not return while the loop might still be setting a connection up.

[What a closing can raise](what-a-closing-can-raise.md) is a subject of its own.

## The fields next

The socket and the subscription's name are taken into local names, and the fields holding them cleared — before anything is sent.

That ordering matters. An opening asked for once the fields are cleared sets up a fresh connection rather than being handed the one being closed.

An opening arriving earlier, while the loop is still being waited on, answers at once instead: the loop is not yet done, which is one of the two reasons an opening does nothing.

## The unsubscribe

An unsubscribe is sent on the local socket. A transport failure, or running out of time, is swallowed.

The request names the subscription only where one was recorded. Where none was, it is sent without one — so the venue is told to unsubscribe without being told from what.

## The socket last

Closed, with a transport failure of that closing passed over.

## What a caller learns

Each of the sending steps passes over the kinds of failure it expects, so a closing that meets only those answers and says nothing about whether the venue heard it.

## Related

- [The venue feed](the-venue-feed.md)
- [What opening the stream does and does not do](what-opening-the-stream-does-and-does-not-do.md)
- [What a closing can raise](what-a-closing-can-raise.md)
