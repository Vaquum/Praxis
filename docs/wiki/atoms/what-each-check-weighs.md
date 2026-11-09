---
row: N2-03
baseline: 49aa659
created: 2026-10-20 10:20 UTC
modified: 2026-10-22 08:39 UTC
reviewed: 2026-10-22 08:39 UTC
evidence:
  - claim: "The three loss windows are the last twenty-four hours, seven days and thirty days, each summing what was lost inside it"
    source: "`nexus/infrastructure/loss_derivation.py` 24-26 and 87-113"
  - claim: "The risk stage walks seven figures in a fixed order against their limits and refuses at the first one over: four about drawdown, three about losses run up over the last day, seven days and thirty"
    source: "`nexus/core/validator/risk_stage.py` 66-108, walked at 111-121"
  - claim: "A figure with no limit set is passed over rather than read as nought"
    source: "`nexus/core/validator/risk_stage.py` 112-113"
  - claim: "A figure the platform stage needs and does not have refuses the decision rather than being passed over"
    source: "`nexus/core/validator/platform_limits_stage.py` 146-148 and 177-178"
  - claim: "The health stage reads none of the decision, refusing on the health snapshot alone"
    source: "`nexus/core/validator/health_stage.py` 356 then 358-365"
  - claim: "The snapshot it reads is five figures handed in, each weighed against whichever of its three thresholds are set, an unset one skipped"
    source: "`nexus/core/validator/health_stage.py` 190-230 and 242-254, the thresholds unset by default at 47-50 and 72-83"
  - claim: "Which way each is weighed, and that a halt outranks a breach and a breach a warning, are the stage's own"
    source: "`nexus/core/validator/health_stage.py` 190-230 and 232-307, only the first two refusing at 358-365"
  - claim: "The capital stage is the one that sets money aside, and the one place a change's new amount is weighed against the standing one"
    source: "`nexus/core/validator/capital_stage.py` 52-61, the weighing at 41-50"
  - claim: "Intake asks a change for an amount above nought and reads nothing about the amount it is replacing"
    source: "`nexus/core/validator/intake_stage.py` 312-318"
  - claim: "What Praxis puts there for a change is a standing one, the same for every change, so that question is answered before it is asked"
    source: "`praxis/launcher.py` 269 and 1112-1122"
  - claim: "Intake reads the order's side and its amount as well, where it is an entry"
    source: "`nexus/core/validator/intake_stage.py` 221-235"
  - claim: "The price stage refuses a decision with no reference price on it, where a deviation cap is set"
    source: "`nexus/core/validator/price_stage.py` 316-336"
---
# What each check weighs

[The checks a decision passes](the-checks-a-decision-passes.md) are six stages, each reading something different. Four read the order; the other two read the account's losses and a health snapshot handed in.

## The account's losses

The risk stage walks seven figures and refuses at the first over its limit: four [measures of how far down the account is](how-far-down-the-account-is.md) — the moment's figure on the whole value and a lifetime peak on closed money, each as amount and fraction — and three about losses over the last day, seven days and thirty. One with no limit is passed over.

## The platform's ceilings

[The platform stage](what-the-platform-ceilings-weigh.md) weighs five things: what the order comes to, and four handed in from a snapshot. A figure it needs and lacks refuses the decision.

## The book, and the account's health

[The price stage](what-the-price-check-weighs.md) refuses on the book's age, its spread and a deviation from a reference, each where a limit for it is set.

The health stage reads none of the decision. It refuses on a snapshot of five figures handed in, each weighed against whichever of its thresholds are set, so one with none is read and never acted on. Which way each is weighed, and that a halt outranks a breach and a breach a warning, are its own; a warning refuses nothing.

## The money

The capital stage [sets money aside](how-nexus-sets-money-aside.md). It holds the only arithmetic that would weigh [a change's](changing-work-already-sent.md) new amount against the standing one, and a change skips it, so that weighing never happens. Intake, which a change does run, asks it for an amount above nought — and what Praxis puts there is a standing one, the same every time, so that question is answered before it is asked. For an entry it reads side and amount.

## Related

- [The checks a decision passes](the-checks-a-decision-passes.md)
- [What the platform ceilings weigh](what-the-platform-ceilings-weigh.md)
- [What the price check weighs](what-the-price-check-weighs.md)
- [How far down the account is](how-far-down-the-account-is.md)
- [How Nexus sets money aside](how-nexus-sets-money-aside.md)

---

Created 2026-10-20 10:20 UTC · Last modified 2026-10-22 08:39 UTC
