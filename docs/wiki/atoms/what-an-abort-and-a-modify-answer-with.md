---
row: N81-01
baseline: 49aa659
created: 2026-11-09 04:07 UTC
modified: 2026-11-09 04:07 UTC
evidence:
  - claim: "An abort is refused where it carries no command name, and that is the only thing it is refused for"
    source: "`nexus/strategy/action_submit.py` 586 into 587-590, the routine holding no other test"
  - claim: "A modify is refused for any of three missing things, weighed in turn: the command name, the mode and the parameters"
    source: "`nexus/strategy/action_submit.py` 626 into 627-630, or 633 into 634-637, or 640 into 641-644"
  - claim: "Both send inside a guard whose catch names any exception, and answer with the failure's own text"
    source: "`nexus/strategy/action_submit.py` 592 into 593-598 and 599, then 604-606, or 647 into 648-655 and 656, then 661-664"
  - claim: "Both answer a success carrying the command name they were given"
    source: "`nexus/strategy/action_submit.py` 613-615, or 671-674"
  - claim: "Every answer a modify gives carries the decision behind it, the field standing empty unless something passes it"
    source: "`nexus/strategy/action_submit.py` 629, or 636, or 643, or 663, or 674, the field standing empty unless passed at 96"
---
# What an abort and a modify answer with

An abort and a modify are the two actions that go out without a command being built, and each answers with one of three things: refused, failed on the way out, or sent.

## What each is refused for

An abort, for carrying no command name — and nothing else. A modify, for any of three missing things, weighed in turn: the command name, the mode, and the parameters.

So a modify can be refused three ways and an abort one, and in both the refusal happens before anything is sent.

## The send

Both send inside a guard whose catch names any exception. A send that raises is answered as a failure carrying the failure's own text, so what went wrong travels back to the caller as words rather than as a kind.

## The success

Both answer carrying the command name they were given. Neither invents one, and neither reads one back from the far side.

## The decision one carries and the other does not

Every answer a modify gives carries the decision behind it. The field stands empty unless something passes it, and [nothing on the abort road passes one](when-a-submission-does-not-reach-capital.md).

So a caller holding a bundle of answers can tie every modify back to the decision that produced it, and no abort to anything but its own command name.

## Related

- [How the walk over a strategy's actions ends each one](how-the-walk-over-a-strategys-actions-ends-each-one.md)
- [How a call across the seam is made](how-a-call-across-the-seam-is-made.md)
