---
row: P160-01
baseline: 49aa659
created: 2026-11-16 00:30 UTC
modified: 2026-11-16 00:30 UTC
evidence:
  - claim: "The cancel goes out first and nothing of what it answers is kept"
    source: "`execution_manager.py` 10274, then 10275"
  - claim: "A cancel the venue has no record of is passed over, leaving the question to the asking that follows"
    source: "`execution_manager.py` 10278, then 10279"
  - claim: "A cancel that fails any other way answers nothing at all"
    source: "`execution_manager.py` 10280, then 10287"
  - claim: "The order is then asked after, and that answer is what comes back"
    source: "`execution_manager.py` 10289, then 10290"
  - claim: "An asking that cannot be answered, the order missing or the venue failing, answers nothing too"
    source: "`execution_manager.py` 10293, then 10300"
  - claim: "The figure the replacement is sized against is read off that answer"
    source: "`execution_manager.py` 8779-8782, the figure taken at 8781"
  - claim: "The road carrying a change through abandons it on that nothing and leaves the order resting"
    source: "`execution_manager.py` 8716, then 8717, then 8723"
  - claim: "The scan over changes still owing passes that change over instead, leaving it for a later pass"
    source: "`execution_manager.py` 8840, then 8843, then 8844"
---
# What an amend asks the venue before it replaces

Changing a single resting order means taking it down and putting another up, and between the two Praxis asks the venue twice: once to cancel, once for what the order ended as.

## Two questions, one answer

The cancel goes out first, and nothing of what it answers is kept. A cancel the venue has no record of is passed over — the order is already gone, and what it went as is the second question's business.

The order is then asked after, and that answer is what comes back to the caller. The figure the replacement is sized against is read off it, which is why the cancel's own reply is of no use here.

## When nothing comes back

A cancel that fails any other way answers nothing. So does an asking that cannot be answered, whether because the venue has no such order or because it would not reply.

Either way the caller is handed nothing, and nothing is the one answer that says where the order stands is unknown — the cancel may have reached it, and it may be resting yet.

## What nothing means to each caller

The road carrying a change through abandons it and leaves the order where it is, so the change is dropped rather than carried on half-done.

[The scan over changes still owing](how-a-change-is-routed-to-its-handler.md) treats the same nothing as a reason to wait: the change is passed over and tried again on a later pass.

## Related

- [How a change is routed to its handler](how-a-change-is-routed-to-its-handler.md)
- [How a single order's amend is named](how-a-single-orders-amend-is-named.md)
