---
row: P49-01
baseline: 49aa659
created: 2026-11-08 17:29 UTC
modified: 2026-11-08 17:29 UTC
evidence:
  - claim: "Each of the five fields is one call into the shared re-keying, which is given the field's name"
    source: "`command_translator.py` 181, or 187, or 193, or 214, or 234"
  - claim: "The name reaches the complaint, so a refusal says which field it was about"
    source: "`command_translator.py` 162-166, or 171-175"
  - claim: "A maker preference left out becomes no preference, before the call is reached"
    source: "`command_translator.py` 212-213"
  - claim: "A self-trade setting left out becomes none, the same way"
    source: "`command_translator.py` 232-233"
  - claim: "One of the five is given a table of equivalences as well, the two sides naming the same thing differently"
    source: "`command_translator.py` 234, the table at 145-150"
---
# The five re-keyings

Five fields of a decision are [re-keyed into Praxis's own names](how-a-decision-becomes-a-command.md), and each is one call into the same shared re-keying.

## What the call is given

The value, the kind of name wanted — and the field's name.

That last is why a refusal can be read: the complaint names the field it was about, rather than reporting that some name among five did not match.

## The two that may be left out

A maker preference left out becomes no preference. A self-trade setting left out becomes none.

Both answer before the shared re-keying is reached, so neither reaches it with nothing to re-key. The other three have no such answer: a decision arriving without one of them refuses the command.

## The one with a table

One of the five needs more than the name it arrived with, the two sides calling the same thing by different words. A small table records which word means which, and the re-keying is given it along with the field's name.

## Related

- [How a decision becomes a command](how-a-decision-becomes-a-command.md)
- [The payload a mode's settings arrive in](the-payload-a-modes-settings-arrive-in.md)
- [The builder that stands apart](the-builder-that-stands-apart.md)
