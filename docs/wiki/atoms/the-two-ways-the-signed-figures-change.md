---
row: N48-01
baseline: 49aa659
created: 2026-11-08 17:25 UTC
modified: 2026-11-08 17:25 UTC
evidence:
  - claim: "The realized figure can be changed through one call, which refuses a figure that is not finite"
    source: "`nexus/core/domain/risk_state.py` 276-278"
  - claim: "That call sets the figure and works the falls out again"
    source: "`nexus/core/domain/risk_state.py` 280-281"
  - claim: "The unrealized figure has a second call, written the same way"
    source: "`nexus/core/domain/risk_state.py` 286-288, setting and recomputing at 290-291"
  - claim: "Neither asks the figure to be at or above nought, since both are signed"
    source: "`nexus/core/domain/risk_state.py` 276, and 286"
  - claim: "Both fields can also be written straight, the record being an ordinary changeable one, and a restoring from the log sets them that way"
    source: "`nexus/core/domain/risk_state.py` 98-99 and 144-145, set at `nexus/infrastructure/wal_codec.py` 306-310"
  - claim: "A straight write leaves the falls as they were, nothing recomputing them"
    source: "`nexus/core/domain/risk_state.py` 280-281 and 290-291 being the only places the recomputing is reached from a change"
---
# The two ways the signed figures change

Two of [the account's figures](what-the-risk-records-refuse.md) are signed: what it has realized, and what it has not. Each has a call of its own for changing it.

## What each call does

It refuses a figure that is not finite. Then it sets the figure, and works the falls out again from it.

Neither asks the figure to stand at or above nought. Both are signed, so a figure below nought is a loss rather than a contradiction.

## The road that skips both

The record is an ordinary changeable one, and both fields can be written straight. [A restoring from the log](what-a-recovery-takes-before-it-rebuilds.md) does exactly that, setting them as the record is built.

A write made that way leaves the falls as they were. Nothing watches the fields, so the falls answer to the last call that recomputed them rather than to the figures standing now.

That is why [a recovery](what-a-recovery-writes-at-the-end.md) ends by handing the realized total back through the call: the straight writes that rebuilt the record left the falls untouched, and the call is what brings them into line.

## Related

- [What the risk records refuse](what-the-risk-records-refuse.md)
- [How far down the account is](how-far-down-the-account-is.md)
- [What a recovery writes at the end](what-a-recovery-writes-at-the-end.md)
