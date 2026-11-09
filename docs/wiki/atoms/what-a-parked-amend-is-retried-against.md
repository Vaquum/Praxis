---
row: P151-02
baseline: 49aa659
created: 2026-11-15 20:00 UTC
modified: 2026-11-15 20:00 UTC
evidence:
  - claim: "An account the manager does not hold ends the retry at once"
    source: "`execution_manager.py` 8830, then 8831 into 8832"
  - claim: "The parked amends are walked over a copy of them, so the walk can drop entries as it goes"
    source: "`execution_manager.py` 8834"
  - claim: "A parked amend whose command the manager no longer holds is dropped and passed over"
    source: "`execution_manager.py` 8835, then 8836 into 8837-8838"
  - claim: "The old order is cancelled and asked after in one step"
    source: "`execution_manager.py` 8840-8842"
  - claim: "An order the venue answers nothing for, or one whose status is not terminal, leaves the amend parked and the walk goes on"
    source: "`execution_manager.py` 8843 into 8844"
  - claim: "Otherwise the amend is driven on, and dropped from the parked ones only where that answers that it finished"
    source: "`execution_manager.py` 8846-8848, then 8849 into 8850"
---
# What a parked amend is retried against

A parked amend is one whose old order had not finished when the amend reached it, and the retry asks the venue again rather than reading what Praxis holds.

## Walking a copy

The parked amends are walked over a copy, which is what lets the walk drop entries as it goes. An amend whose command the manager no longer holds is dropped and passed over — the command went while the amend waited.

## What the venue is asked

The old order is cancelled and asked after in one step. An order the venue answers nothing for, and one whose status is not terminal, both leave the amend parked and the walk carries on to the next.

So an amend waits for the venue to agree that the old order is finished, however many passes that takes, and nothing here gives up on it.

## When it is dropped

Only where driving the amend on answers that it finished. An amend driven and left unfinished stays parked, so the same pass next time will cancel and ask again.

## Related

- [How an amend's replacement order goes out](how-an-amends-replacement-order-goes-out.md)
- [Changing work already sent](changing-work-already-sent.md)
- [A change waiting out a hold](a-change-waiting-out-a-hold.md)
