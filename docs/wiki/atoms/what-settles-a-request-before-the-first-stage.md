---
row: N7-10
baseline: 49aa659
created: 2026-10-27 20:10 UTC
modified: 2026-10-27 22:00 UTC
evidence:
  - claim: "A strategy name that is not identical to itself stripped is refused as the host's settings are read"
    source: "`nexus/infrastructure/manifest.py` 136-142"
  - claim: "The builder works from the names those settings carried, and answers with nothing for a name it does not know"
    source: "`praxis/launcher.py` 4144-4146 into 4180-4191"
  - claim: "A share at or below nought, or above a hundred, is refused as those settings are read, and a pool at or below nought there and again as the figures are built"
    source: "`nexus/infrastructure/manifest.py` 159-161 and 250-252, and `nexus/core/domain/capital_state.py` 44-46"
  - claim: "The budget is written as the request is built, not before: the pool at that strategy's share of it for an entry or an exit, with nothing deployed taken off"
    source: "`praxis/launcher.py` 1129-1132 into `nexus/core/capital_controller/capital_controller.py` 459-462"
  - claim: "A change is written with its budget at nought instead, answering inside its own branch"
    source: "`praxis/launcher.py` 1117 inside 1112-1124"
  - claim: "A change passes the test that nought would otherwise fail, being named in the exemption"
    source: "`nexus/core/validator/intake_stage.py` 427-431"
---
# What settles a request before the first stage

The strategy name a request carries is settled as the host's settings are read, and its budget is written as the request itself is built — as is [its sum](what-an-entrys-sum-is-worked-out-from.md).

## The name

A name that is not identical to itself stripped is refused as those settings are read. The builder then works from the names they carried, and answers with nothing for a name it does not know — so no request is built under a name [the first stage](what-the-first-stage-weighs-before-the-mode.md) could refuse for it.

## The budget

A share at or below nought, or above a hundred, is refused as the settings are read, and a pool at or below nought there and again as the figures are built.

So the budget written for an entry or an exit is the pool at that strategy's share of it, with nothing deployed taken off: a strategy that has spent everything it had arrives with the budget it started with. Both operands being above nought, nought is not a figure that working out reaches in practice.

## The change that carries a nought

[A change](changing-work-already-sent.md) is written with its budget at nought instead, and never reaches that working out. It is named in the test's own exemption, so the nought does it no harm.

## Related

- [What an entry's sum is worked out from](what-an-entrys-sum-is-worked-out-from.md)
- [What the first stage weighs before the mode](what-the-first-stage-weighs-before-the-mode.md)

---

Created 2026-10-27 20:10 UTC · Last modified 2026-10-27 22:00 UTC
