---
row: N2-05
baseline: 49aa659
created: 2026-10-20 14:40 UTC
modified: 2026-10-26 23:30 UTC
evidence:
  - claim: "Each reservation carries a moment it expires at, the clock read as it is granted plus the life asked for"
    source: "`nexus/core/capital_controller/capital_controller.py` 407-414"
  - claim: "One claimed past that moment is released and the claim refused"
    source: "`nexus/core/capital_controller/capital_controller.py` 563-572"
  - claim: "A claim naming an order already tracked raises, before the reservation is looked up at all"
    source: "`nexus/core/capital_controller/capital_controller.py` 549-552 before 553"
  - claim: "A sweep takes one at the expiry moment itself, where a claim at that same moment is still in time"
    source: "`nexus/core/capital_controller/capital_controller.py` 480 against 563"
  - claim: "Past that, a reservation the record no longer holds is refused as not found, whether it was given back or swept"
    source: "`nexus/core/capital_controller/capital_controller.py` 553-559"
  - claim: "A reservation can also be given back outright, by name, which takes its amount off what is set aside and off what that strategy is deploying"
    source: "`nexus/core/capital_controller/capital_controller.py` 501-526, asked for at `nexus/strategy/action_submit.py` 485-491"
  - claim: "Past the claim its own amount has left that bucket, and what a send failing outright undoes is the tracked order instead"
    source: "`nexus/core/capital_controller/capital_controller.py` 591-593, the undoing at `praxis/launcher.py` 1990-1994 into `nexus/core/capital_controller/capital_controller.py` 1064-1081, reached from `nexus/strategy/action_submit.py` 389-399 and from `praxis/launcher.py` 2201-2207"
  - claim: "Expired ones are swept where a reservation is asked for, and where a claim gets as far as looking its own up, on each of that claim's three ways out; releasing one and acknowledging an order sweep none"
    source: "`nexus/core/capital_controller/capital_controller.py` 327, and 556 or 568 or 578, against 501-526 and 597-642"
  - claim: "A claim naming an order already tracked raises before that lookup and sweeps nothing"
    source: "`nexus/core/capital_controller/capital_controller.py` 549-551 before 553 and 578"
  - claim: "A sweep gives each expired amount back and takes it off what that strategy is recorded as deploying"
    source: "`nexus/core/capital_controller/capital_controller.py` 482-499"
  - claim: "A claim in time moves the amount from set aside to in flight unchanged, the sweep running first, so the total deployed can fall across it by other reservations' amounts"
    source: "`nexus/core/capital_controller/capital_controller.py` 578 before 592-593"
  - claim: "A claim too late takes the claimed reservation's own amount off instead"
    source: "`nexus/core/capital_controller/capital_controller.py` 563-572"
  - claim: "Praxis claims it as it registers the command, before the send where the receiving side was taken as bound to the name sent and after it where it was not"
    source: "`praxis/launcher.py` 2086-2093 and 2102 built only at 4239-4254, against 4287-4293"
  - claim: "Where the claim comes back a failure the registration is dropped, but only where this attempt put it there"
    source: "`praxis/launcher.py` 2082 and 2094-2101"
  - claim: "Where it raises instead, for an order already tracked, the registration is left standing"
    source: "`nexus/core/capital_controller/capital_controller.py` 549-551 raising past `praxis/launcher.py` 2094, caught at `nexus/strategy/action_submit.py` 313-334"
  - claim: "Nexus offers a road of its own to the claim and no code there walks it"
    source: "`nexus/strategy/action_submit.py` 566-577, no caller for it anywhere under `nexus/`"
---
# What becomes of money set aside

[Money set aside for a trade](how-nexus-sets-money-aside.md) carries a moment it expires at — the clock as granted, plus the life asked for — and ends by being claimed, given back, or swept.

## Claimed, or refused

A claim naming an order already tracked raises before the reservation is looked up. Past that, one made after the expiry releases it and refuses; one the record no longer holds is refused as not found.

A claim in time moves the amount from what is set aside into what is in flight, unchanged. One can be given back by name instead, taking its amount off that and off the strategy's deployment — what [a command refused before any claim](what-nexus-does-when-a-command-does-not-get-across.md) asks for. Past the claim its amount has left that bucket, and what a send failing outright undoes is the order instead.

## When the figures catch up

Expired reservations are swept where one is asked for, and where a claim gets as far as looking its own up — nowhere else, so one nobody claims counts against the limits until such a call. The claim that raises before that lookup sweeps nothing.

A sweep gives each expired amount back and takes it off that strategy's deployment, taking one at the expiry moment itself, where a claim arriving then is still in time. So a claim can see the total fall by other amounts.

## Who claims it

Praxis claims it as it registers the command, [on one side of the send or the other](when-money-set-aside-moves-onto-an-order.md). Before the send, a claim coming back a failure drops the registration — only where this attempt put it there — and raises, which Nexus catches as a failed submission; one that raises outright leaves it standing.

Nexus offers a road no code there walks.

## Related

- [How Nexus sets money aside](how-nexus-sets-money-aside.md)
- [What Nexus does when a command does not get across](what-nexus-does-when-a-command-does-not-get-across.md)

---

Created 2026-10-20 14:40 UTC · Last modified 2026-10-26 23:30 UTC
