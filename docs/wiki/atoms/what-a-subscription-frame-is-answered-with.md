---
row: P91-02
baseline: 49aa659
created: 2026-11-09 07:16 UTC
modified: 2026-11-09 07:16 UTC
evidence:
  - claim: "A frame that will not read as JSON is dropped in silence, and so is one that reads as anything but an object"
    source: "`praxis/binsim/server.py` 840-841 into 842-843, then 845 into 846"
  - claim: "The frame's own identifier is read with an empty one standing in, so a frame naming none is still answered"
    source: "`praxis/binsim/server.py` 848"
  - claim: "Any method but the one it serves is answered with a refusal rather than dropped"
    source: "`praxis/binsim/server.py` 849, then 851 into 852-859, then 861"
  - claim: "The parameters are read only where they came as an object, each of the two values taken as nothing otherwise"
    source: "`praxis/binsim/server.py` 863, then 864, and 865"
  - claim: "Each value is trimmed where it is text and taken as empty where it is anything else"
    source: "`praxis/binsim/server.py` 867, and 868"
  - claim: "Either of them coming to nothing is answered with a refusal"
    source: "`praxis/binsim/server.py` 870 into 871-878, then 880"
  - claim: "A key the ledger matches to no account is answered with a refusal of its own"
    source: "`praxis/binsim/server.py` 882 into 883-890, then 892"
  - claim: "A frame that passed everything is answered with a number taken from the shared counter"
    source: "`praxis/binsim/server.py` 894, then 896-900"
---
# What a subscription frame is answered with

A text frame arriving on binsim's answering socket meets five tests, and which test it fails decides whether it is answered or dropped.

## The two that drop it

A frame that will not read as JSON is dropped in silence. So is one that reads as anything but an object. Neither gets a reply, so a caller sending malformed text learns nothing at all.

## The three that refuse it

Any method but the one it serves. Either of the two values it needs coming to nothing. A key the ledger matches to no account. Each is answered with a refusal rather than dropped.

So the line between silence and a refusal is whether the frame was readable: every frame binsim could parse gets an answer, and silence means the parsing failed.

## How the values are read

The frame's own identifier is read with an empty one standing in, so a frame naming none is still answered. The parameters are read only where they came as an object, each of the two values taken as nothing otherwise. Each is then trimmed where it is text and taken as empty where it is anything else.

So a value sent as a number, a list or nothing at all arrives at the test as empty, and is refused the same way as a value left blank.

## What a pass is worth

A number taken from the shared counter. That number is the whole of what the caller gets.

## Related

- [The two sockets binsim accepts](the-two-sockets-binsim-accepts.md)
