---
row: P158-01
baseline: 49aa659
created: 2026-11-09 12:21 UTC
modified: 2026-11-09 12:21 UTC
evidence:
  - claim: "The pair is asked after by its list name, and each leg that list names is asked after in turn"
    source: "`execution_manager.py` 7543, then 7544, then 7547, then 7548"
  - claim: "A leg standing at anything but an ended standing answers that the pair is still working, and no further leg is asked after"
    source: "`execution_manager.py` 7551 into 7552"
  - claim: "A list the venue has no record of answers that nothing of the pair is working"
    source: "`execution_manager.py` 7553, then 7554"
  - claim: "A venue failure anywhere in the asking answers that the pair is still working"
    source: "`execution_manager.py` 7555, then 7561"
  - claim: "Every leg at an ended standing answers that nothing is working"
    source: "`execution_manager.py` 7563"
  - claim: "A candidate answered as still working stops the close before anything is placed"
    source: "`execution_manager.py` 7627, then 7628, then 7636"
  - claim: "The asking is done before the position's remainder is counted"
    source: "`execution_manager.py` 7627, then 7638"
---
# How a cancelled protection pair is judged still working

Before Praxis closes a position by hand, it asks the venue whether any leg of the [protective pair](protection.md) it has just cancelled is still working.

## The asking

The pair is asked after by its list name, and each leg that list names is asked after in turn. A leg standing at anything but an ended standing answers that the pair is still working, and the legs after it go unasked.

Every leg at an ended standing answers that nothing of the pair is working, which is the answer the close needs.

## The two answers a failure gives

A list the venue has no record of answers that nothing is working. The pair cannot be resting under a name the venue never heard, so the close goes on.

A venue failure anywhere in the asking answers the opposite: the pair is still working. So a question the venue will not answer counts the same as a leg found resting, and the close is stopped by a line that is about the venue's health rather than the pair's.

## What rides on the answer

[The close](when-a-flatten-places-nothing.md) asks after every name the cancelled pair could still rest under, and one answered as still working stops it before anything is placed. The asking is done before the remainder is even counted, so a pair found still working costs the questions and nothing else.

## Related

- [When a flatten places nothing](when-a-flatten-places-nothing.md)
- [Protection](protection.md)
- [When protection is lost](when-protection-is-lost.md)
