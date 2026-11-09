---
row: N7-03
baseline: 49aa659
created: 2026-10-27 08:14 UTC
modified: 2026-10-27 08:14 UTC
evidence:
  - claim: "The first stage refuses a strategy name that is not identical to itself with its surrounding whitespace stripped, before it reads anything else"
    source: "`nexus/core/validator/intake_stage.py` 404-410"
  - claim: "It then refuses a request whose sum is nought, exempting an exit, an abandonment, a cancellation and a change by name, of which only an exit and a change ever arrive"
    source: "`nexus/core/validator/intake_stage.py` 412-424, an abandonment sent before the walk at `nexus/strategy/action_submit.py` 201-203 and no request built for a cancellation among the four a strategy asks for at `nexus/strategy/action.py` 29-32"
  - claim: "It then refuses one against a strategy whose budget is nought, exempting the same four"
    source: "`nexus/core/validator/intake_stage.py` 425-440"
  - claim: "The mode is read after those three, and the stage's own hooks after the mode"
    source: "`nexus/core/validator/intake_stage.py` 442-444 after 404-440, and 446-447 after that"
  - claim: "Each of the three refusals names this stage and carries a code of its own"
    source: "`nexus/core/validator/intake_stage.py` 405-409, or 418-422, or 435-439"
  - claim: "A change is built with both its sum and its budget at nought"
    source: "`praxis/launcher.py` 1115-1117 inside 1112-1124"
  - claim: "The name a request carries is settled as the settings are read, while its budget and its sum are written as the request is built"
    source: "`nexus/infrastructure/manifest.py` 136-142, against the writing at `praxis/launcher.py` 1251 and 1129-1132"
---
# What the first stage weighs before the mode

[The walk's first stage](what-each-check-weighs.md) weighs three things about a request before it reads [the trading mode](what-the-halted-mode-turns-away.md): the strategy's name, the sum asked for, and the strategy's budget.

## The order

A strategy name that is not identical to itself with its surrounding whitespace stripped is refused first. Then a request whose sum is nought, and then one against a strategy whose budget is nought.

The mode comes after those three, and the stage's own hooks after the mode. Each of the three refusals names this stage and carries a code of its own, so a caller that trips one can tell which.

## Who the last two apply to

Each of those two exempts an exit, an abandonment, [a cancellation](how-a-trade-is-cancelled.md) and [a change](changing-work-already-sent.md) by name. Of those four only an exit and a change ever arrive: [an abandonment](the-roads-around-the-checks.md) is sent before the walk is asked for, and no request is built for a cancellation. So the two tests bear on an entry, and an exit and a change pass them whatever their figures say.

A change leans on that entirely: it is built with both its sum and its budget at nought, and passes because it is named rather than because its figures clear anything.

## Where the three figures come from

The name is settled as the host's settings are read; the budget and the sum are [written as the request is built](what-settles-a-request-before-the-first-stage.md), which decides which of these three a live request can trip.

## Related

- [What settles a request before the first stage](what-settles-a-request-before-the-first-stage.md)
- [What each check weighs](what-each-check-weighs.md)

---

Created 2026-10-27 08:14 UTC · Last modified 2026-10-27 08:14 UTC
