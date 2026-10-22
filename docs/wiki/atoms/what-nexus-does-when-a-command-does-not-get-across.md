---
row: N1-02
baseline: 49aa659
created: 2026-10-16 09:30 UTC
modified: 2026-10-22 21:00 UTC
reviewed: 2026-10-22 21:00 UTC
evidence:
  - claim: "Money is set aside partway through the staged checks, so a later stage can refuse with it already held, and that releases it"
    source: "`nexus/strategy/action_submit.py` 242 and 260 into 273"
  - claim: "A stage that raises returns a failure and releases nothing"
    source: "`nexus/strategy/action_submit.py` 241-258 against 260-273"
  - claim: "Nexus's own catches are for ordinary failures, an interrupt going straight past them"
    source: "`nexus/strategy/action_submit.py` 241 and 313, catching `Exception` rather than `BaseException`"
  - claim: "Praxis catches an interrupt once the claim has run, undoes what it can, and lets it go on"
    source: "`praxis/launcher.py` 2135-2207 into 1987-2009"
  - claim: "Only the two stages after the one that sets money aside can raise with any held, the order putting it fourth of six"
    source: "`nexus/core/validator/pipeline_models.py` 50-57"
  - claim: "One that cannot be turned into a command releases it"
    source: "`nexus/strategy/action_submit.py` 292-300"
  - claim: "A send failing with a registration in hand hands the undoing to it, and the plain release is not reached on that road"
    source: "`nexus/strategy/action_submit.py` 397-399 against 408-409"
  - claim: "A registration raising before it claims reaches the release, which gives the money back"
    source: "`praxis/launcher.py` 2078 then `nexus/strategy/action_submit.py` 313-325 into 485-491"
  - claim: "A claim refused for being too late has already given its own amount back, so the release that follows finds nothing"
    source: "`nexus/core/capital_controller/capital_controller.py` 563-575"
  - claim: "One raising after the claim undoes the order first and then reaches the release, which finds the reservation gone and logs"
    source: "`praxis/launcher.py` 2201-2207 into 1980-2009, the release missing at `nexus/strategy/action_submit.py` 485-500"
  - claim: "In Praxis it runs a callback against the position, drops the command's registration where this attempt wrote it, and takes the order's money back only where the reservation was claimed"
    source: "`praxis/launcher.py` 1987-1988 and 2005-2009, the money at 1990-1994"
  - claim: "Undoing through it is allowed to fail, logged, with no release behind it"
    source: "`nexus/strategy/action_submit.py` 397-409"
  - claim: "Where that failure escapes the taking instead, the release does follow, and finds the reservation already gone"
    source: "`praxis/launcher.py` 2201-2207 out to `nexus/strategy/action_submit.py` 313-325"
  - claim: "A send that times out marks a registration unknown rather than undoing it"
    source: "`nexus/strategy/action_submit.py` 338-341"
  - claim: "In Praxis that marking writes a record against the command and leaves the money alone"
    source: "`praxis/launcher.py` 1961-1978"
  - claim: "Marking it is itself allowed to fail, and that is logged"
    source: "`nexus/strategy/action_submit.py` 342-344"
  - claim: "Which road a timeout takes turns on whether a registration was taken, nothing about the money being read"
    source: "`nexus/strategy/action_submit.py` 339 against 379"
  - claim: "A release asked for without a controller to ask returns having released nothing"
    source: "`nexus/strategy/action_submit.py` 485-486"
  - claim: "A timeout with a registration is reported unknown, carrying the command's name"
    source: "`nexus/strategy/action_submit.py` 361-369"
  - claim: "A timeout without one is reported failed and carries no such name"
    source: "`nexus/strategy/action_submit.py` 380-388"
---
# What Nexus does when a command does not get across

[What was set aside](how-nexus-sets-money-aside.md) for a trade that does not get through is undone by a release, by the registration taken before the handover, or not at all.

## Released

Money is set aside partway through the checks, so a later stage can refuse with it held — and that refusal asks for a release, as does a decision that cannot become a command. Neither releases without one.

A stage that raises rather than refusing returns the failure and releases nothing. Money is set aside at the fourth of six, so only the two after it raise with any held.

Nexus's catches are for ordinary failures, an interrupt going past them. Praxis catches one once the claim has run, undoes what it can, and lets it go on.

## Undone through the registration instead

A send failing with a registration in hand gives the undoing to it, with no plain release. In Praxis it runs a callback against the position, drops this attempt's registration and any bracket exit, and takes the order's money back only where [it was claimed](what-becomes-of-money-set-aside.md).

A registration that raises rather than returning goes the other way: the release runs. Before the claim it gives the money back; after it, or after an undoing that raised, it finds nothing.

## Not undone at all

A send that runs out of time marks the registration unknown and undoes nothing, the command having possibly arrived. In Praxis that writes a record and leaves the money.

Marking may fail too, and is logged.

A timeout with no registration asks for a release instead.

## What the caller hears

A timeout with a registration is reported unknown, carrying the command's name, which any later settling works from. One without is reported failed, with none.

## Related

- [How Nexus sets money aside](how-nexus-sets-money-aside.md)
- [When a send's outcome is unknown](when-a-send-is-unclear.md)

---

Created 2026-10-16 09:30 UTC · Last modified 2026-10-22 21:00 UTC
