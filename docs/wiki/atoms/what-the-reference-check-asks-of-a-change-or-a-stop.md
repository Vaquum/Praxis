---
row: N82-03
baseline: 49aa659
created: 2026-11-13 17:00 UTC
modified: 2026-11-13 17:00 UTC
evidence:
  - claim: "The hook holds one answer and hands it back at the end, rather than answering from inside a branch"
    source: "`nexus/core/validator/intake_stage.py` 219, handed back at 330, the hook itself handed back at 332"
  - claim: "A change asks a provider for the commands it may name where one was given, and otherwise reads the set captured as the hook was built"
    source: "`nexus/core/validator/intake_stage.py` 289-293"
  - claim: "No set at all denies the change, before its name is ever looked at"
    source: "`nexus/core/validator/intake_stage.py` 295 into 296-301"
  - claim: "A change naming nothing, or naming something the set does not hold, is denied"
    source: "`nexus/core/validator/intake_stage.py` 302-305 into 306-311"
  - claim: "A change asking for no size, or a size at or below nought, is denied"
    source: "`nexus/core/validator/intake_stage.py` 312 into 313-318"
  - claim: "A stop naming nothing, or naming something the active set does not hold, is denied"
    source: "`nexus/core/validator/intake_stage.py` 320-321 into 323-328"
  - claim: "A stop has no provider to ask, reading only the set captured as the hook was built"
    source: "`nexus/core/validator/intake_stage.py` 321, against 289-293"
  - claim: "Each of the four actions is weighed on a branch of its own, so no request meets two of these checks"
    source: "`nexus/core/validator/intake_stage.py` 237, or 288, or 320"
---
# What the reference check asks of a change or a stop

The hook that checks what a request refers to weighs each kind of request on a branch of its own, and holds one answer that it hands back at the end.

## How it answers

One answer, assigned wherever a check fails and handed back once at the end. Nothing returns from inside a branch, so every road through the hook passes the same single exit.

Each kind of request is weighed on a branch of its own, so no request meets two of these checks.

## A change

Three things are asked, in turn. First, which commands may be named: a provider is asked where one was given, and otherwise the set captured as the hook was built is read. No set at all denies the change, before its name is ever looked at.

Then the name itself — nothing, or something the set does not hold, is denied. Then the size: none, or one at or below nought, is denied.

## A stop

One thing is asked: the name, against the set of active commands. Nothing, or something that set does not hold, is denied.

A stop has no provider to ask. It reads only the set captured as the hook was built, where a change can be told the current one — so a command that became stoppable after the hook was made is unknown to a stop and known to a change.

## Related

- [What the intake stage holds its hooks to](what-the-intake-stage-holds-its-hooks-to.md)
- [What intake asks of an exit](what-intake-asks-of-an-exit.md)
