---
row: N53-01
baseline: 49aa659
created: 2026-11-08 17:48 UTC
modified: 2026-11-08 17:48 UTC
evidence:
  - claim: "Each action is submitted inside a bound context naming the strategy and the kind of action"
    source: "`nexus/strategy/action_submit.py` 191-193 into 200"
  - claim: "The trade and the command are named in it too, where the action carries them"
    source: "`nexus/strategy/action_submit.py` 195-196, or 197-198"
  - claim: "An abort is answered inside that context before any context for the checks is built"
    source: "`nexus/strategy/action_submit.py` 201-203"
  - claim: "A builder of the checks' context that raises an ordinary failure is caught, and the action answered as a failed submission carrying the builder's words"
    source: "`nexus/strategy/action_submit.py` 205-221"
  - claim: "The actions after it are still submitted"
    source: "`nexus/strategy/action_submit.py` 222, which goes on to the next"
---
# What each action is submitted inside

Every action a strategy asks for is submitted inside [a bound context](what-the-nexus-logging-adds.md) of its own, so everything written while it is handled carries the same few fields.

## What is bound

The strategy's name and the kind of action, always. The trade's name and the command's name as well, where the action carries them.

So a line written anywhere inside the submitting carries those names without the writing site having to pass them. Nothing names the action itself, so two entries from one strategy are told apart only by what else they carry.

## The fork inside it

An abort is answered first, inside the context but before any context for [the checks](the-checks-a-decision-passes.md) is built. It goes its own road and the next action follows.

## The builder that fails

The context the checks need is built per action. A builder that raises an ordinary failure is caught: the action is answered as a submission that failed, carrying the builder's own words as the reason. A failure of the kinds that unwind a program is not caught here and leaves the turn.

The actions after it are still submitted, so one action whose context cannot be built costs that action and nothing else. What it costs is recorded in the answers the submitting returns to its caller, rather than told to the strategy.

## Related

- [The roads around the checks](the-roads-around-the-checks.md)
- [What the Nexus logging adds](what-the-nexus-logging-adds.md)
- [When a submission does not reach capital](when-a-submission-does-not-reach-capital.md)
