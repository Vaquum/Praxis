---
row: P89-03
baseline: 49aa659
created: 2026-11-09 07:07 UTC
modified: 2026-11-09 07:07 UTC
evidence:
  - claim: "A refusal is built as a body carrying a code and a message, in the venue's own shape"
    source: "`server.py` 738"
  - claim: "One status becomes a bad-request and one a service-unavailable, each handed back for the caller to raise"
    source: "`server.py` 740 into 741, or 743 into 744"
  - claim: "Any other status raises there and then instead of being handed back"
    source: "`server.py` 746"
  - claim: "A depth asked for with no figure answers a default"
    source: "`server.py` 751 into 752"
  - claim: "A figure that will not read as a whole number is refused, carrying what arrived"
    source: "`server.py` 754-755 into 756 into 757-760"
  - claim: "A figure at or below nought, or past the cap, is refused with a message naming the cap"
    source: "`server.py` 762 into 763-766"
  - claim: "A figure that passes both is answered as it stands"
    source: "`server.py` 768"
---
# The two shapes a refusal takes

A refusal from binsim is a body carrying a code and a message, in the venue's own shape — and the routine that builds one behaves differently depending on the status asked for.

## The two it builds

One status becomes a bad-request and one a service-unavailable. Each is handed back for the caller to raise, so the caller decides where the refusal is thrown from.

## The one it refuses to build

Any other status raises there and then instead of being handed back. So a caller asking for a status the builder does not know gets an error thrown at them, where a caller asking for one it knows gets an error to throw.

The two are easy to confuse in reading: both are exceptions, and only one of them is the caller's to raise.

## The reading of a depth

A depth asked for with no figure answers a default. A figure that will not read as a whole number is refused, carrying what arrived. A figure at or below nought, or past the cap, is refused with a message naming the cap. A figure that passes both is answered as it stands.

So three of the four roads through the reading end in the caller's hands as a figure or a refusal, and the refusals say which of the two tests the figure failed.

## Related

- [What binsim's read endpoints answer](what-binsims-read-endpoints-answer.md)
