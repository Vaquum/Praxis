---
row: N81-02
baseline: 49aa659
created: 2026-11-13 15:30 UTC
modified: 2026-11-13 15:30 UTC
evidence:
  - claim: "The answers are gathered into a list made before the walk starts, one for each action the walk reaches"
    source: "`nexus/strategy/action_submit.py` 188, then 190"
  - claim: "Each road that ends an action early appends its answer and moves straight to the next action"
    source: "`nexus/strategy/action_submit.py` 239, or 274 into 281, or 288, or 309, or 410 into 418"
  - claim: "A modify leaves on a road of its own before a command is ever built"
    source: "`nexus/strategy/action_submit.py` 283 into 284-287, then 288"
  - claim: "Building the command stands inside a guard, and a build that raises ends that action as a failed sending"
    source: "`nexus/strategy/action_submit.py` 290-291 into 301-308"
  - claim: "The road that sent needs no moving on, its appending being the last thing the walk's body does"
    source: "`nexus/strategy/action_submit.py` 446-453, standing last before 455"
  - claim: "The whole list is answered once the walk is done, and nothing is answered before then"
    source: "`nexus/strategy/action_submit.py` 455"
---
# How the walk over a strategy's actions ends each one

A strategy's actions are walked one at a time, and each ends with exactly one answer added to a list.

## The list

Made before the walk starts. Every road through an action appends to it, so the number of answers matches the number of actions the walk reached.

## Moving on

Each road that ends an action early appends its answer and moves straight to the next action. There is no shared ending the roads come back to — each carries its own answer and leaves.

A modify leaves on a road of its own, before a command is ever built for it.

## The building

Building the command stands inside a guard. A build that raises ends that action as a failed sending, and the walk goes on to the next.

## The road that sent

It needs no moving on: its appending is the last thing the walk's body does, so the next action follows naturally.

## When anything is answered

Once the walk is done, and not before. A caller gets every answer at once or none — so a walk that raises part-way through gives back nothing, however many actions it had already finished.

## Related

- [What an abort and a modify answer with](what-an-abort-and-a-modify-answer-with.md)
- [What a strategy is handed](what-a-strategy-is-handed.md)
