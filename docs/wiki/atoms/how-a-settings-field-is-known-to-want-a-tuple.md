---
row: P36-01
baseline: 49aa659
created: 2026-11-08 16:42 UTC
modified: 2026-11-08 16:42 UTC
evidence:
  - claim: "A field is taken to want a tuple where its declared kind is a tuple, bare or with its members named"
    source: "`command_translator.py` 96-97"
  - claim: "Any annotation wrapped round the declaration is stripped off first"
    source: "`command_translator.py` 94 into 109-112"
  - claim: "A union is walked, and a field declaring one that holds a tuple is taken to want a tuple"
    source: "`command_translator.py` 99-100"
  - claim: "Nothing else is walked, so a tuple inside another kind of generic is not taken for one"
    source: "`command_translator.py` 102, reached for every other kind"
  - claim: "The fields are read off every record in the two tables as the module is loaded, before any payload arrives"
    source: "`command_translator.py` 135-138 into 142-144"
  - claim: "A record both tables name is read twice over, the tables being joined without dropping a repeat, and one answer kept"
    source: "`command_translator.py` 135-138 holding it twice, 143 keeping one entry per record"
  - claim: "Only the fields a record is built with are classed as wanting a tuple, though every field's declaration is resolved first"
    source: "`command_translator.py` 128 filtering, after 123 resolves them all"
---
# How a settings field is known to want a tuple

[A mode's settings](the-payload-a-modes-settings-arrive-in.md) arriving as a mapping have some of their lists made into tuples. Which fields those are is read off the records Praxis keeps, from what each field declares.

## What counts

A field declaring a tuple — bare, or with its members named. A field declaring a union that holds one, which is how a settings field that may be left out is written.

Any annotation wrapped around the declaration is stripped off before either test, so a field carrying one is read as the kind underneath it.

## What does not

A union is the only thing walked into. A field declaring a list of tuples, or any other kind holding a tuple inside it, is left alone — the list that arrives for it stays a list.

So the coercion reaches a field that is a tuple and a field that may be a tuple, and nothing that merely contains one.

## When it is worked out

As the module loads, for every record the two tables of settings name — the one for a command's settings and the one for a change's. The two are joined without dropping a repeat, so a record both name is read twice and one answer kept.

Every field's declaration is resolved in the reading; only the fields a record is built with are classed as wanting a tuple, so a field the record works out for itself is read and then passed over.

A payload therefore cannot change which of its lists become tuples: that was settled by the record's own declarations before any payload arrived.

## Related

- [The payload a mode's settings arrive in](the-payload-a-modes-settings-arrive-in.md)
- [How a decision becomes a command](how-a-decision-becomes-a-command.md)
- [The change each way of working accepts](the-change-each-way-of-working-accepts.md)
