---
row: N53-02
baseline: 49aa659
created: 2026-11-12 10:30 UTC
modified: 2026-11-12 11:00 UTC
evidence:
  - claim: "Turning a submission into a tracked order is skipped where its status is anything but submitted"
    source: "`nexus/strategy/action_submit.py` 552-557"
  - claim: "It is skipped where a submitted one carries no command name, and that is reported as a warning"
    source: "`nexus/strategy/action_submit.py` 559-564"
  - claim: "It is skipped where there is no decision, or a decision with no money set aside"
    source: "`nexus/strategy/action_submit.py` 566-571"
  - claim: "An abort is answered as submitted with no decision at all, having bypassed the checks"
    source: "`nexus/strategy/action_submit.py` 201-203 into 613-616"
  - claim: "Money is set aside before the command is sent, not after it is answered"
    source: "`nexus/strategy/action_submit.py` 313-315 ahead of 337"
  - claim: "A send that times out is answered as unknown, carrying its command name and its decision, with the setting aside already done"
    source: "`nexus/strategy/action_submit.py` 338-341 into 361-370"
---
# When a submission does not reach capital

Turning a submission into [a tracked order](what-a-tracked-order-must-be.md) is skipped in three cases. None of them means the money was left alone.

## The three skips

A status that is anything but submitted.

A submitted one carrying no command name — reported as a warning, since the capital side would have nothing to match a later outcome against.

No decision at all, or a decision that set no money aside.

## What the third one catches

An abort is answered as submitted and carries no decision, having bypassed [the checks](the-checks-a-decision-passes.md) entirely. An exit and a change do pass the checks and carry a decision, and neither sets money aside.

So for three kinds of action out of four the third skip is simply how they end.

## Why a skip is not an untouched account

The money is set aside before the command is sent, not after it is answered.

So a send that times out is answered as unknown — carrying its command name and its decision — and skipped here by the first case, with the setting aside already done and [the handover already registered](what-a-pending-sale-is.md). The skip means no tracked order was made from this answer, and nothing more.

## Related

- [How Nexus sets money aside](how-nexus-sets-money-aside.md)
- [What each action is submitted inside](what-each-action-is-submitted-inside.md)
- [What a tracked order must be](what-a-tracked-order-must-be.md)
