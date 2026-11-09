---
row: P4-42
baseline: 49aa659
created: 2026-10-13 06:50 UTC
modified: 2026-11-16 13:30 UTC
evidence:
  - claim: "Every live scheme is frozen, each freeze written down before it takes hold in memory"
    source: "`execution_manager.py` 6626, then 6630-6638, then 6639, then 6640, the names answered at 6642"
  - claim: "A scheme already held for protection or draining is passed over, and any other hold is overwritten with the protection one"
    source: "`execution_manager.py` 6627-6628 against 6638"
  - claim: "The failure record refuses a revision below the first, so an unamended pair's zero is raised to one before it is written"
    source: "`execution_manager.py` 6911 against `praxis/core/domain/events.py` 91, reached from 1162"
  - claim: "The failure record is written before closing the remaining position is attempted"
    source: "`execution_manager.py` 6918-6920 before 6938-6941"
  - claim: "The closing order is attempted only where the policy is to flatten and halt"
    source: "`execution_manager.py` 6933-6941"
  - claim: "A pair whose standing is unknown is watched, and one found resting is taken up again instead"
    source: "`execution_manager.py` 7388-7392"
  - claim: "A leg query that fails, or fills that will not settle, return without reaching the deadline, so the pair can stay unknown past it"
    source: "`execution_manager.py` 7442-7443 and 7457-7458, reached from 7398, against the deadline at 7511-7513"
  - claim: "One still unanswerable waits out a deadline and is then taken as lost on the record alone"
    source: "`execution_manager.py` 7395 into 7512-7513, remediated at 7523"
  - claim: "A pair gone with nothing left to protect ends the bracket rather than counting as lost, reporting a close only where the exit filled"
    source: "`execution_manager.py` 7464 into 7469-7480"
  - claim: "A deadline passed with nothing left on the books leaves the pair unknown instead"
    source: "`execution_manager.py` 7519-7521"
  - claim: "A pair that never goes up enters the same answer directly"
    source: "`execution_manager.py` 7181-7185, then 7186-7190, reached from 4958-4963, the failure recorded at 10025-10032, then 10033"
  - claim: "An account named in no policy setting gets the flattening one"
    source: "`trading_config.py` 220-221 against 26-28, wired at `trading.py` 232"
  - claim: "The word to Nexus is kept under the command's name and offered at once"
    source: "`execution_manager.py` 6733-6740, offered at 6943"
  - claim: "It is offered again on each protection scan, where a raise in one job cannot skip the other six"
    source: "`execution_manager.py` 6789-6791 driven from 7292, each job tried at 7298-7301"
  - claim: "A handover that raises is logged and left waiting"
    source: "`execution_manager.py` 6792-6799"
  - claim: "A handover that lands is written down, and a restart passes over a command already written down as told"
    source: "`execution_manager.py` 6801-6808, read back at 6757-6764"
---
# When protection is lost

Protection is lost when the [protective pair](protection.md) guarding a filled position is settled gone, stays unknown past a deadline, or never goes up — in each case with exposure still on the books. A pair merely unknown is watched, and that watch can find it resting. With nothing left to protect, one gone ends the bracket. The deadline binds only the unanswerable case: where asking about a leg fails, or its fills will not settle, the watch returns before reaching it, and the pair can stay unknown past it. Praxis answers a loss in a fixed order: freeze, record, close out, tell Nexus.

## Frozen against adding more

Every live [scheme](work-fed-out-over-time.md) on the account is frozen against a further slice, each freeze written to [the record](the-event-spine.md) before it takes hold — so a restart resumes it frozen.

A scheme held for a failed slice takes the protection hold instead, so no amend restarts it. One already protection-held, or draining, is left alone.

## The record comes before the close

The failure is written down next, naming which revision of the pair it was — and refusing a revision below the first, so an unamended pair's zero is raised to one.

Only then is [the remainder closed out](when-a-flatten-places-nothing.md), and only where the account's policy is to flatten and halt. The other leaves it standing; an account named in neither gets the flattening one.

## Told as soon as it can be

The word to Nexus is kept under the command's name, offered at once, then on each protection scan until it lands. One that raises is logged and left waiting.

One that lands is written down too, and only that stops a restart offering it again — [the hold it places](the-holds-a-report-places.md) is lifted by hand.

## Related

- [Protection](protection.md)
- [When protection is put up again](when-protection-is-put-up-again.md)
- [When a flatten places nothing](when-a-flatten-places-nothing.md)
- [The holds a report places](the-holds-a-report-places.md)

---

Created 2026-10-13 06:50 UTC · Last modified 2026-10-14 13:10 UTC
