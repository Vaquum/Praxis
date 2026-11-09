---
row: P119-01
baseline: 49aa659
created: 2026-11-15 04:00 UTC
modified: 2026-11-15 10:30 UTC
evidence:
  - claim: "The kind of action is looked up in a fixed mapping, and one the mapping does not hold is reported and dropped"
    source: "`launcher.py` 1101, then 1102 into 1110, asked through 4193"
  - claim: "A change is answered inside its own branch, carrying no sum, no fee and no budget, a placeholder size, and the name of the command it means to amend"
    source: "`launcher.py` 1112 into 1113-1124"
  - claim: "An abort is answered with nothing at all"
    source: "`launcher.py` 1126 into 1127"
  - claim: "The strategy's budget is worked out only after both of those have answered"
    source: "`launcher.py` 1129-1132, past 1112 and 1126"
  - claim: "An entry is sent to a builder given a price to fall back on and a symbol to use, where an exit's builder is given the thing that turns a scrap to dust instead"
    source: "`launcher.py` 1134 into 1135-1145, against 1147-1156"
  - claim: "A change's symbol is the same one an entry would use, whatever the command it amends was placed against"
    source: "`launcher.py` 1121, against 1143"
---
# How an action is routed into a request

A strategy's action becomes a request the checks can read, and which of four kinds it is settles how much of that request is filled in.

## The kind

Looked up in a fixed mapping. One the mapping does not hold is reported and dropped, so an action of an unknown kind reaches no check at all.

## The two that answer early

A change is answered inside its own branch, carrying no sum, no fee and [no budget](what-settles-a-request-before-the-first-stage.md) — a placeholder size standing where a real one would, and the name of the command it means to amend.

An abort is answered with nothing at all, so nothing is built for it here.

## Why the order matters

The strategy's budget is worked out only after both of those have answered. So a change and an abort never reach the money at all, and a run of either costs nothing to work out.

## The two that go further

An entry is sent to a builder given a price to fall back on and a symbol to use. An exit's builder is given the thing that turns a scrap to dust instead.

That difference is where [a dusted scrap](what-a-dusted-scrap-leaves-behind.md) comes from: only the exit's builder holds anything able to do it, so only an exit can end that way.

## The symbol a change carries

The same one an entry would use, whatever the command it amends was placed against. So the symbol in a change's request says nothing about the order being amended.

## Related

- [What settles a request before the first stage](what-settles-a-request-before-the-first-stage.md)
- [What an entry's sum is worked out from](what-an-entrys-sum-is-worked-out-from.md)
- [What Praxis works out for an exit](what-praxis-works-out-for-an-exit.md)
