---
row: N2-04
baseline: 49aa659
created: 2026-10-20 12:30 UTC
modified: 2026-10-21 19:00 UTC
evidence:
  - claim: "The account's whole value is what it started with, plus what it has made and closed, plus what open positions are up or down"
    source: "`nexus/core/domain/risk_state.py` 238-239"
  - claim: "A second value leaves open positions out, counting what the account started with plus what it has made and closed"
    source: "`nexus/core/domain/risk_state.py` 238"
  - claim: "Each value keeps a high mark that only ever rises, seeded from what the account started with"
    source: "`nexus/core/domain/risk_state.py` 240-251"
  - claim: "How far down the account is on its whole value, and that as a share of its high mark, are worked out fresh each time"
    source: "`nexus/core/domain/risk_state.py` 253-257"
  - claim: "The worst it has ever been down on closed money, and that worst as a share, are records that only ever rise"
    source: "`nexus/core/domain/risk_state.py` 258, 264 and 266-267"
  - claim: "The worst it has ever been down on its whole value is kept the same way and handed to no stage of the walk"
    source: "`nexus/core/domain/risk_state.py` 268-271 against 316-324"
  - claim: "The mode controller reads it instead, against two limits of its own, and holds the account where either is passed"
    source: "`nexus/core/mode_controller.py` 398-412, its limits taken at 70"
  - claim: "Those limits are a separate set from the walk's, nothing in Nexus tying the two together"
    source: "`nexus/core/mode_controller.py` 70 against `nexus/core/validator/risk_stage.py` 25-31"
  - claim: "A high mark of nothing gives a share of nothing rather than dividing by it"
    source: "`nexus/core/domain/risk_state.py` 254-255 and 261-262"
---
# How far down the account is

Nexus keeps two figures for what the account is worth. The whole value is what it started with, plus what it has made and closed, plus whatever open positions are up or down. The closed-money value leaves that last part out, so an open position that has moved does not show in it.

## The marks each value is measured from

Each value keeps a high mark that only ever rises, seeded from what the account started with, so a mark reached once is kept after the value falls back and the first trade is measured against the starting figure.

## Four figures, measured two ways

How far down the account is on its whole value, and that as a share of its high mark, are worked out fresh every time: they fall back to nothing when the value recovers.

The worst it has ever been down on closed money, and that worst as a share, are records that only rise: a bad week stays in them after the account recovers.

A high mark of nothing gives a share of nothing rather than dividing by it.

## The figure nothing reads

The worst the account has ever been down on its whole value is kept the same way as the other records, and handed to no stage of the walk: [the stage that weighs drawdown](what-each-check-weighs.md) never sees it.

What reads it is the part of Nexus deciding whether the account may trade at all. It weighs that worst against two limits of its own and holds the account where either is passed. Those limits are a separate set from the walk's, tied to it by nothing, so one can be loose where the other is tight.

## Related

- [What each check weighs](what-each-check-weighs.md)

---

Created 2026-10-20 12:30 UTC · Last modified 2026-10-21 19:00 UTC
