---
row: P4-43
baseline: 49aa659
created: 2026-10-13 06:50 UTC
modified: 2026-10-13 06:50 UTC
evidence:
  - claim: "A shortfall has three answers, applied by the account's own handler"
    source: "`nexus/core/domain/reconciliation_mismatch_response.py` 19-21, applied at `nexus/reconciler/reconciliation_handler.py` 79-82"
  - claim: "A lost protection has two"
    source: "`nexus/core/domain/bracket_protection_failure_response.py` 29-30, applied at `nexus/reconciler/protection_remediation_handler.py` 78-81"
  - claim: "Left out of the settings, a shortfall halts and a lost protection flattens and halts"
    source: "`nexus/infrastructure/manifest.py` 316-317 and 334-335"
  - claim: "A word naming neither answer is refused as the settings are read"
    source: "`nexus/infrastructure/manifest.py` 319-324 and 337-344"
  - claim: "Halted while any halting hold stands or health says halted, entries blocked while any blocking one does or health says so, otherwise health alone"
    source: "`nexus/core/mode_controller.py` 488-493"
  - claim: "A halted account names the first of five causes, one with entries blocked the first of two, and health where no hold applies"
    source: "`nexus/core/mode_controller.py` 527-537, 539-546 and 548"
  - claim: "A hold placed while it already stands keeps the first reason and moment, halting and blocking alike"
    source: "`nexus/core/mode_controller.py` 433-438 and 458-461"
  - claim: "Each hold has a lift that nothing in the running system calls, the blocking pair included"
    source: "`nexus/core/mode_controller.py` 167, 188, 206 and 227, placed from 158, 179, 197 and 218"
  - claim: "A shortfall handed over is remembered in memory alone, so a restart can report the same one again"
    source: "`trading.py` 251 and 1287, read at 1264"
  - claim: "A finding addressed to an account whose Nexus side has not been published raises, leaving it undelivered"
    source: "`launcher.py` 3016-3023 and 3027-3034 into 3972-3977"
---
# The holds a report places

A hold is a flag on an [account](what-an-account-is.md) forcing how it may trade. Two findings Praxis reports put one on: [a balance that falls short](when-a-balance-shortfall-is-reported.md) and [a protection that was lost](when-protection-is-lost.md).

## What each account chooses

A shortfall has three answers: halt the account, block new entries while letting exits through, or log it alone. A lost protection has two: flatten and halt, or block new entries.

Each is read from [the account's settings](the-settings-a-host-is-given.md). Left out, a shortfall halts and a lost protection flattens and halts. A word naming no answer is refused as those settings are read, so the host never starts.

## Halt outranks the rest

The account is halted while any halting hold stands, and halted too where [its health](health.md) says halted — health outranks a hold that only blocks entries. Entries are blocked where a blocking hold stands or health asks it, and otherwise health alone decides.

A halted account names its cause, taking the first of shutdown, by hand, risk, shortfall, protection; one with entries blocked takes shortfall before protection. A mode from health rather than a hold names health.

A hold placed while it already stands keeps the reason and the moment of the first placing.

## Lifted only from outside

Each hold has a matching lift that nothing in the running system calls, so it stands until something outside the process clears it. So Praxis writes a protection down as handed over, and a restart passes over one written down. A shortfall is remembered in memory alone, and a restart can report the same one again, re-placing a hold lifted meanwhile.

## A finding that arrives too early

A finding addressed to an account whose Nexus side is not yet published raises, leaving it undelivered and bringing it round next cycle.

## Related

- [When a balance shortfall is reported](when-a-balance-shortfall-is-reported.md)
- [When protection is lost](when-protection-is-lost.md)
- [What a reconciliation tells Nexus](what-a-reconciliation-tells-nexus.md)

---

Created 2026-10-13 06:50 UTC · Last modified 2026-10-13 06:50 UTC
