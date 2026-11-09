---
row: P160-02
baseline: 49aa659
created: 2026-11-09 12:26 UTC
modified: 2026-11-09 12:26 UTC
evidence:
  - claim: "The intent is recorded and applied before the send"
    source: "`execution_manager.py` 7779, then 7780, then 7782"
  - claim: "A venue failure is first put to a rescue by the order's own name"
    source: "`execution_manager.py` 7791, then 7792"
  - claim: "A rescue that finds nothing records the failure and ends the send there"
    source: "`execution_manager.py` 7795, then 7802, then 7810"
  - claim: "A rescue that finds the order stands in for the answer the send would have given"
    source: "`execution_manager.py` 7812"
  - claim: "The closing command is installed, its trade remembered and the order's name mapped to it only once an answer is in hand"
    source: "`execution_manager.py` 7814, then 7815, then 7816, against 7810"
  - claim: "The send is then recorded and applied"
    source: "`execution_manager.py` 7818, then 7825, then 7826"
  - claim: "Each fill the venue reported as it placed is recorded against the closing command"
    source: "`execution_manager.py` 7828, then 7829-7844, the command named at 7836"
  - claim: "Only a fill the record answered with a place is carried into the figures"
    source: "`execution_manager.py` 7845, then 7846 into 7847"
---
# What is written down when a flatten goes out

Closing a position by hand is recorded in the order the writes fall: the intent before the venue hears of it, the send once the venue answers, and each fill the venue gives as it takes the order.

## Before the venue hears

The intent goes down first and is applied to the record, so the order exists in the record before it exists at the venue.

## When the send fails

A venue failure is first put to a rescue by the order's own name, which asks the venue whether the order arrived after all.

A rescue that finds nothing records the failure and ends the send there. One that finds the order stands in for the answer the send would have given, and everything after it runs as though the send had succeeded.

## After the answer

The closing command is installed, its trade remembered, and the order's name mapped to it — all three only once an answer is in hand, so a send that ended in a recorded failure installs no command at all.

The send is then recorded and applied.

## The fills that came with it

A venue can fill a market order as it takes it, and each such fill is recorded against the closing command rather than the order it closes. Only a fill the record answered with a place is carried into the figures, so a fill written twice counts once.

## Related

- [When a flatten places nothing](when-a-flatten-places-nothing.md)
- [How big a flatten goes out](how-big-a-flatten-goes-out.md)
- [How an unfinished close is recovered](how-an-unfinished-close-is-recovered.md)
