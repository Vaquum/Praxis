---
row: N38-02
baseline: 49aa659
created: 2026-11-11 20:00 UTC
modified: 2026-11-11 20:30 UTC
evidence:
  - claim: "A recovery ends by handing the realized figure back to the risk record"
    source: "`nexus/infrastructure/state_store.py` 333"
  - claim: "That figure is the sum over what each strategy realized, which the risk record works out itself"
    source: "`nexus/infrastructure/state_store.py` 333 reading the record's own total"
  - claim: "Handing it back works the fall out again from that total"
    source: "`nexus/core/domain/risk_state.py` 253 and 258"
  - claim: "The peak it is measured against is kept at whichever is largest: the peak restored from the snapshot, what the account started with, or the total just handed back"
    source: "`nexus/core/domain/risk_state.py` 247-251, the stored peak restored at `nexus/infrastructure/wal_codec.py` 313"
  - claim: "The worst fall ever recorded is kept at whichever is larger, the stored one or the one just worked out"
    source: "`nexus/core/domain/risk_state.py` 266, the stored one restored at `nexus/infrastructure/wal_codec.py` 318"
---
# What a recovery writes at the end

Once the figures are rebuilt, a recovery makes one more write that nothing in the log asked for: it hands the realized figure back to [the risk record](how-far-down-the-account-is.md).

## The figure it hands back

The risk record works out its own total over what each strategy realized. A recovery reads that total and sets it as the record's cumulative figure.

## What the handing back does

The fall is worked out again from that total. What it is measured against is not: the peak is kept at whichever is largest of the peak restored from the snapshot, what the account started with, and the total just handed back.

The worst fall ever recorded is kept the same way, at whichever is larger of the stored figure and the one just worked out.

So a recovery can rebuild a smaller total than the snapshot held and still report the snapshot's worst fall, the stored figure standing because it is the larger. What the log rebuilds moves the current fall; the records that only rise are left where they were unless the new figures exceed them.

## Related

- [What a recovery takes before it rebuilds](what-a-recovery-takes-before-it-rebuilds.md)
- [How far down the account is](how-far-down-the-account-is.md)
- [What the thirty-day cut leaves](what-the-thirty-day-cut-leaves.md)
