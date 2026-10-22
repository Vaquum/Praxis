---
row: N2-06
baseline: 49aa659
created: 2026-10-21 16:00 UTC
modified: 2026-10-22 15:00 UTC
reviewed: 2026-10-22 15:00 UTC
evidence:
  - claim: "The platform stage weighs what the order comes to in money against a ceiling, reading that off the decision itself, and only where the ceiling is set"
    source: "`nexus/core/validator/platform_limits_stage.py` 130-143, the ceiling unset by default at 41"
  - claim: "It then weighs an order rate, a projected holding, a day's losses and how much of the pool is committed, each taken from a snapshot handed in"
    source: "`nexus/core/validator/platform_limits_stage.py` 145-160, 161-175, 176-188 and 190-205"
  - claim: "Each of those four runs only where a limit for it is set, and refuses the decision where the limit is set and the figure absent"
    source: "`nexus/core/validator/platform_limits_stage.py` 145-148, 161-164, 176-178 and 190-193"
  - claim: "It stops at the first refusal, every later check standing down once one is made"
    source: "`nexus/core/validator/platform_limits_stage.py` 145, 161, 176 and 190"
  - claim: "The snapshot Praxis builds carries the projected holding and nothing else"
    source: "`praxis/launcher.py` 617-623"
  - claim: "That projection is worked out from the account's live positions, the lock held only long enough to copy the list of them"
    source: "`praxis/launcher.py` 618-619 before 576-580"
  - claim: "It adds up what is held in the order's own pair, counting a holding bought as positive and any other as negative, adds the order itself, and floors the total at nothing"
    source: "`praxis/launcher.py` 576-597"
  - claim: "An order sized in money alone is turned into an amount at a middle price, and adds nothing where no middle price is to be had"
    source: "`praxis/launcher.py` 583-595"
  - claim: "A holding the account did not buy is counted against the sum, positions kept on either side"
    source: "`praxis/launcher.py` 576-580, either side allowed at `nexus/core/domain/position.py` 66-68"
  - claim: "The negation written for the incoming order is never reached down this road, the stage being skipped for every action but an entry and an entry having to buy"
    source: "`praxis/launcher.py` 592-593 against `nexus/core/validator/pipeline_executor.py` 162-175 and `nexus/core/validator/intake_stage.py` 221-228"
  - claim: "The positions in that copy are the live ones, their sizes written to as reports come in"
    source: "`nexus/infrastructure/praxis_connector/outcome_processor.py` 488 and 559"
---
# What the platform ceilings weigh

The platform stage is the last of [the checks a decision passes](the-checks-a-decision-passes.md). It weighs five things, only the first read off the decision itself.

## The one it can see for itself

What the order comes to in money is weighed against a ceiling, where one is set. The figure is on the decision already.

## The four it has to be handed

An order rate, a projected holding, a day's losses and how much of the pool is committed come from a snapshot handed in. Each runs where a limit is set for it, and refuses where the figure is then absent.

The stage stops at the first refusal, later checks standing down once one is made.

## What actually arrives

The snapshot Praxis builds carries the projected holding alone: what the order's pair holds, plus the order's amount, floored at nothing. A holding the account did not buy counts against it, positions being kept either way, and an order sized in money becomes an amount at a middle price — where none is to be had it adds nothing. The negation written for the incoming order is never reached: the stage is skipped for all but an entry, and an entry has to buy.

The lock is held only long enough to copy the list of positions. Those in the copy are the live objects, their sizes written to as reports come in, so the figure can be read mid-change.

Every one of the five is unset by default, so a stage with no ceilings passes everything. Of the four from the snapshot only the projected holding can be weighed: a limit on the order rate, the day's losses or the pool committed refuses any decision reaching that check, the figure being absent.

## Related

- [The checks a decision passes](the-checks-a-decision-passes.md)
- [What each check weighs](what-each-check-weighs.md)

---

Created 2026-10-21 16:00 UTC · Last modified 2026-10-22 15:00 UTC
