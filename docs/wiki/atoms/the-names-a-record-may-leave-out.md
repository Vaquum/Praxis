---
row: P61-07
baseline: 49aa659
created: 2026-11-12 19:30 UTC
modified: 2026-11-12 19:30 UTC
evidence:
  - claim: "The shared test for a name takes a flag saying the name may be absent, and answers early where it is set and the name is nothing at all"
    source: "`_require_str.py` 25-26, the early answer given only where the flag is set"
  - claim: "Setting that flag does not allow an empty name: the early answer is given for nothing at all and for no other value, so an empty one falls to the ordinary refusal"
    source: "`_require_str.py` 25 testing for nothing at all, ahead of 28-30"
  - claim: "Seven of the ninety calls the event records make set it"
    source: "`events.py` 1960, and 1961, and five more among the ninety"
  - claim: "The ordinary refusal turns away whatever counts as nothing, which takes in an empty name, nothing at all, nought and false"
    source: "`_require_str.py` 28-30"
---
# The names a record may leave out

[The shared test every record uses on a name](what-every-event-is-held-to.md) takes a flag saying that name may be absent, and seven of the ninety calls the event records make set it.

## What the flag does

Where it is set and the name is nothing at all, the test answers early and the name passes.

## What it does not do

The early answer is given for nothing at all, and for no other value. An empty name offered where absence is allowed therefore falls through to the ordinary refusal and is turned away.

So a record declaring a name optional accepts its absence and refuses it written as emptiness — two things a writer is likely to treat as one.

## The ordinary refusal

Without the flag, the test turns away whatever counts as nothing. That takes in an empty name, nothing at all, nought, and false.

It asks nothing about kind, so a name that is a number or a list passes either way.

## Related

- [What every event is held to](what-every-event-is-held-to.md)
- [What a command's checks let through](what-a-commands-checks-let-through.md)
