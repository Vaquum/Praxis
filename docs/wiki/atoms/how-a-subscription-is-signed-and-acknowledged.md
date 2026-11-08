---
row: P68-03
baseline: 49aa659
created: 2026-11-13 01:00 UTC
modified: 2026-11-13 01:00 UTC
evidence:
  - claim: "The request carries the account's key, a window in milliseconds and the moment in milliseconds"
    source: "`binance_ws.py` 206, then 207-211"
  - claim: "The three are joined in the order their names sort, and that joined text is what the secret signs"
    source: "`binance_ws.py` 212, then 213"
  - claim: "The signature is added to the parameters after the signing, so it never signs itself"
    source: "`binance_ws.py` 214, standing after 213"
  - claim: "The request is given a fresh name of its own and sent as text"
    source: "`binance_ws.py` 216-220, then 221"
  - claim: "The answer is waited for with a limit, and running out of time is raised again as a running out naming the account"
    source: "`binance_ws.py` 223-226, then 227-229"
  - claim: "An answer arriving as anything but text is refused with a complaint naming the kind of frame"
    source: "`binance_ws.py` 231-236"
  - claim: "A failure of the subscribing closes the socket just opened and raises on, where the failure is a transport one, a running out of time, or the venue refusing"
    source: "`binance_ws.py` 181, naming the three"
  - claim: "A failure of any other kind leaves the socket open and unheld, nothing in the setting up having recorded it yet"
    source: "`binance_ws.py` 181 naming three kinds, with the recording at 186 not yet reached"
  - claim: "The closing of that socket passes over a transport failure alone, so a failure of another kind there takes the place of the one being reported"
    source: "`binance_ws.py` 182, naming the one kind"
---
# How a subscription is signed and acknowledged

Opening [the venue feed](the-venue-feed.md) means asking the venue for the account's own news, and the asking is signed.

## What is signed

The request carries three things: the account's key, a window in milliseconds, and the moment in milliseconds.

Those three are joined in the order their names sort, and the joined text is what the account's secret signs. Sorting is what makes the text the same for one set of values however they were assembled.

The signature is added to the parameters only after the signing. So it is never part of what it signs.

## Sending it

The request is given a fresh name of its own, so the answer to it can be told from anything else arriving, and is sent as text.

## The answer

It is waited for with a limit. Running out of time is caught and raised again as a running out naming the account, so a caller is told which account went quiet.

An answer arriving as anything but text is refused with a complaint naming the kind of frame that came. That is before the body is read at all.

## When the asking fails

A failure of the subscribing closes the socket just opened and raises on — where the failure is one of three kinds: a transport one, a running out of time, or the venue refusing.

A failure of any other kind leaves that socket open and held by nothing, the setting up not having recorded it yet.

The closing itself passes over a transport failure alone. A failure of another kind there takes the place of the one being reported, so the complaint a caller sees is usually the one about the subscription and not always.

## Related

- [The venue feed](the-venue-feed.md)
- [The address the stream will accept](the-address-the-stream-will-accept.md)
