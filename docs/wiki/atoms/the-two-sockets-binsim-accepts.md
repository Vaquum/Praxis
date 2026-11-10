---
row: P91-01
baseline: 49aa659
created: 2026-11-09 07:16 UTC
modified: 2026-11-09 07:16 UTC
evidence:
  - claim: "Both sockets are opened with the same heartbeat and prepared against the request before anything is read"
    source: "`praxis/binsim/server.py` 821 then 822, and 916 then 917"
  - claim: "The first takes the ledger and the shared counter off the application before it opens"
    source: "`praxis/binsim/server.py` 818, and 819"
  - claim: "It then reads every frame, skipping any that is not text and handing each text frame on"
    source: "`praxis/binsim/server.py` 824 into 825-826, then 828"
  - claim: "The second reads every frame too and does nothing with any of them, leaving its loop only on a close or an error"
    source: "`praxis/binsim/server.py` 919 into 920-921"
  - claim: "Both answer the socket itself once their reading has ended"
    source: "`praxis/binsim/server.py` 830, and 923"
  - claim: "The application itself is given out as it stands"
    source: "`praxis/binsim/server.py` 962"
---
# The two sockets binsim accepts

Binsim accepts two socket connections. One answers what is sent to it; the other accepts and discards.

## What they share

Both are opened with the same heartbeat and prepared against the request before anything is read. Both answer the socket itself once their reading has ended.

So a caller opening either gets a connection that stays up on the same cadence, and learns which it opened only from what comes back.

## The one that answers

It takes the ledger and the shared counter off the application before it opens. It then reads every frame, skipping any that is not text, and hands each text frame on to be answered.

## The one that discards

It reads every frame too, and does nothing with any of them. It leaves its loop only on a close or an error.

So a caller sending a subscription down this socket is answered with silence, and cannot tell its message from one that was acted on.

## Why the second exists at all

Accepting a connection and dropping what arrives keeps client code working that would otherwise fail on the connect. Nothing is pushed down it, because what the real venue pushes there, binsim learns by polling instead.

## Related

- [What the application is handed and what it serves](what-the-application-is-handed-and-what-it-serves.md)
- [What a subscription frame is answered with](what-a-subscription-frame-is-answered-with.md)
