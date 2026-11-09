---
row: N1-04
baseline: 49aa659
created: 2026-10-16 15:40 UTC
modified: 2026-10-23 07:08 UTC
evidence:
  - claim: "A refusal must name the stage that made it, a reason code and a message, neither of the last two blank"
    source: "`nexus/core/validator/pipeline_models.py` 247-261"
  - claim: "An allowed answer must carry none of those three"
    source: "`nexus/core/validator/pipeline_models.py` 226-261"
  - claim: "A reservation either answer carries is checked for being one before the rest of the shape"
    source: "`nexus/core/validator/pipeline_models.py` 229-233 before 235"
  - claim: "An answer that is not a decision at all raises, named for the stage that gave it, before the answer is read for anything else"
    source: "`nexus/core/validator/pipeline_executor.py` 52-56 before 58"
  - claim: "A refusal naming a stage other than the one that made it raises too"
    source: "`nexus/core/validator/pipeline_executor.py` 59-64, inside the refusal branch at 58"
  - claim: "An allowed answer naming a stage never reaches that test, raising as it is made"
    source: "`nexus/core/validator/pipeline_models.py` 235-238"
  - claim: "A stage that raises returns no answer, so the walk hands out nothing"
    source: "`nexus/core/validator/pipeline_executor.py` 51 against 78"
---
# What a check must answer with

Each of [the checks a decision passes](the-checks-a-decision-passes.md) answers by allowing the decision or refusing it, and the walk refuses to guess at anything else.

## A refusal says who and why

A refusal names the stage that made it, a reason code, and a message. The stage has to be one of the six, and neither the code nor the message may be blank.

That is what makes a refusal usable further out: the caller is handed which check stopped the decision rather than only that something did.

## An allowance carries no reason

An allowed answer must carry none of those three, and one built with a reason attached raises as it is made rather than being read either way.

What either answer may carry is [a reservation](how-nexus-sets-money-aside.md), and that is checked for being one before the rest of the shape is looked at.

## Two ways to be unreadable

A stage answering with something that is not a decision raises, named for the stage that did it, before the answer is read for anything else.

A stage refusing while naming a different stage raises as well. That one is already a refusal, so nothing gets past it; what is wrong is the name. The raise stops the refusal going out at all, rather than letting it out blamed on a check that did not make it. An allowed answer never reaches this test, one naming a stage raising as it is made.

## A stage that raises

A stage that raises rather than answering ends the walk with no decision at all. Nothing is handed out, and any reservation the walk was carrying is neither passed on nor released — which is why [the roads that give money back](what-nexus-does-when-a-command-does-not-get-across.md) do not all run through here.

## Related

- [The checks a decision passes](the-checks-a-decision-passes.md)
- [What Nexus does when a command does not get across](what-nexus-does-when-a-command-does-not-get-across.md)

---

Created 2026-10-16 15:40 UTC · Last modified 2026-10-23 07:08 UTC
