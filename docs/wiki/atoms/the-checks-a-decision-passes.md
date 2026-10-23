---
row: N1-03
baseline: 49aa659
created: 2026-10-16 15:00 UTC
modified: 2026-10-23 09:00 UTC
evidence:
  - claim: "The checks are a configured list walked in order, by default intake, risk, price, capital, health, then platform limits"
    source: "`nexus/core/validator/pipeline_models.py` 50-57, walked at `nexus/core/validator/pipeline_executor.py` 47"
  - claim: "A list leaving a stage out, repeating one, or naming one with nothing to run is refused as the walk is built"
    source: "`nexus/core/validator/pipeline_executor.py` 88-93, 95-97 and 110-114"
  - claim: "Which actions skip is decided by the action alone, nothing about the decision being weighed"
    source: "`nexus/core/validator/pipeline_executor.py` 162-168"
  - claim: "An exit and a change skip five of the six, leaving intake alone"
    source: "`nexus/core/validator/pipeline_executor.py` 162-176, reached at 48"
  - claim: "Intake is the one stage no action skips"
    source: "`nexus/core/validator/pipeline_executor.py` 170-176, the set it returns naming the other five"
  - claim: "Only an entry's answer carries a reservation, the stage that grants one being the stage an exit and a change skip"
    source: "`nexus/core/validator/capital_stage.py` 60-61 against `nexus/core/validator/pipeline_executor.py` 162-176"
  - claim: "Claiming that reservation is a separate step, Praxis making it as it registers the command"
    source: "`praxis/launcher.py` 2086-2093"
  - claim: "The context a stage reads is built with its own requirements on the fields it carries, whichever action it is"
    source: "`nexus/core/validator/pipeline_models.py` 113-205"
  - claim: "A denial carrying no reservation of its own is answered with the one an earlier stage granted"
    source: "`nexus/core/validator/pipeline_executor.py` 65-72"
  - claim: "A reservation a stage grants stands until another grants one, and is handed out with an allowed decision"
    source: "`nexus/core/validator/pipeline_executor.py` 75-76 and 78"
---
# The checks a decision passes

A decision from a strategy is walked through a list of checks before Praxis hears it, stopping at the first refusal — unless it came by [one of the roads around the walk](the-roads-around-the-checks.md).

## The order is configured

The list is given rather than fixed, and walked in order: intake, risk, price, capital, health, platform limits by default. One leaving a stage out, repeating one, or naming one with nothing to run is refused as the walk is built, so every stage exists even where an action skips it.

[Money is set aside](how-nexus-sets-money-aside.md) partway along, so a later check refuses a decision already holding capital. Only an entry's answer carries a reservation, the stage that grants one being the stage an exit and a change skip.

## Most of them are skipped for some actions

An exit and [a change](changing-work-already-sent.md) skip risk, price, capital, health and platform limits, leaving intake the only stage to refuse them. [What each of the five weighs](what-each-check-weighs.md) differs, some reading the order and some the state of the account or the venue. Which actions skip them is decided by the action alone. [Two entries in that set, and the roads around the walk entirely](the-roads-around-the-checks.md), are their own matter.

The context a stage reads carries its own requirements on its fields, whatever the action.

## What comes out

An allowed decision carries whatever reservation a stage granted; where a later one grants none the earlier stands, and a refusing stage's own overrides it.

A refusal carries it too where that stage has none, leaving [the release that follows](what-nexus-does-when-a-command-does-not-get-across.md) something to give back. [What a refusal says for itself](what-a-check-must-answer-with.md) is its own matter.

## Related

- [What each check weighs](what-each-check-weighs.md)
- [The roads around the checks](the-roads-around-the-checks.md)
- [What a check must answer with](what-a-check-must-answer-with.md)
- [How Nexus sets money aside](how-nexus-sets-money-aside.md)
- [What Nexus does when a command does not get across](what-nexus-does-when-a-command-does-not-get-across.md)

---

Created 2026-10-16 15:00 UTC · Last modified 2026-10-23 09:00 UTC
