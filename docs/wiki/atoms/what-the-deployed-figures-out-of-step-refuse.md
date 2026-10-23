---
row: N3-08
baseline: 49aa659
created: 2026-10-22 19:10 UTC
modified: 2026-10-22 19:10 UTC
evidence:
  - claim: "Money set aside is refused while the strategies' own figures do not add up to the account's total deployed"
    source: "`nexus/core/capital_controller/capital_controller.py` 340-365"
  - claim: "That total is four figures added together: the money in positions, in working orders, in orders in flight, and set aside"
    source: "`nexus/core/capital_controller/capital_controller.py` 331-336"
  - claim: "The refusal names what it wants done, asking for the deployment to be reconciled before anything new is set aside"
    source: "`nexus/core/capital_controller/capital_controller.py` 343-346, or 352-359"
  - claim: "What it stops is a request to set money aside, which an entry makes and nothing else does"
    source: "`nexus/core/capital_controller/capital_controller.py` 361-365 reached from `nexus/core/validator/capital_stage.py` 49-57, every other kind passed over at `nexus/core/validator/pipeline_executor.py` 162-176 and 47-49"
  - claim: "It is refused too where the total stands above nought with no strategy figure at all"
    source: "`nexus/core/capital_controller/capital_controller.py` 340-346"
  - claim: "The refusal is read before any limit is weighed"
    source: "`nexus/core/capital_controller/capital_controller.py` 361-365 ahead of 369-394"
  - claim: "A sale, an abort, a cancel and a change skip the stage that asks for it, along with four others, the walk passing over each stage it is told to"
    source: "`nexus/core/validator/pipeline_executor.py` 162-176, passed over at 47-49"
  - claim: "A change asking for no more money than it already holds is allowed inside that stage before anything is asked for"
    source: "`nexus/core/validator/capital_stage.py` 41-47"
  - claim: "A strategy's figure is dropped where a taking-out leaves it within a millionth of a millionth of nought, so a sale can close a difference while the account runs"
    source: "`nexus/core/capital_controller/capital_controller.py` 1097-1113, reached at 806, the amount at `nexus/core/domain/capital_state.py` 16"
  - claim: "Each strategy's figure is brought back to the positions at a start"
    source: "`nexus/core/capital_controller/capital_controller.py` 214-272"
  - claim: "The money-in-positions part of that total is set from the positions the host is asked for, in a pass of its own that logs the change"
    source: "`nexus/startup/sequencer.py` 363 into 412-415 into 468-478"
---
# What the deployed figures out of step refuse

Two records of committed money are kept — one per strategy, one for the account — and while they disagree, no new money is set aside.

## The refusal

Before any limit is weighed, the strategies' figures are added up and compared with the account's total — itself four figures added together: the money in positions, in working orders, in orders in flight, and already set aside. A difference refuses the request outright, as does a total standing above nought with no strategy figure at all. The refusal names what it wants done: the deployment reconciled before anything new is set aside.

## What it reaches

Less than it sounds. A sale, an abort, a cancel and a change skip the stage that asks for money altogether, along with four other stages, the walk passing over each one it is told to. Inside that stage, a change asking for no more than it already holds is allowed before anything is asked for.

What the refusal stops is the request to set money aside, which an entry makes and nothing else does.

## How they come back into step

Each strategy's figure is [worked out again from the positions](what-a-boot-rebuilds-from-the-positions.md) at a start. The money-in-positions part of the total they are weighed against is set from the positions the host is asked for, in a pass of its own that logs the change. Both happen at a start. A difference can also close itself while the account runs: a taking-out that leaves a strategy within a millionth of a millionth of nought drops that strategy from the figures rather than keeping a remainder.

## Related

- [What a boot rebuilds from the positions](what-a-boot-rebuilds-from-the-positions.md)
- [How Nexus sets money aside](how-nexus-sets-money-aside.md)

---

Created 2026-10-22 19:10 UTC · Last modified 2026-10-22 19:10 UTC
