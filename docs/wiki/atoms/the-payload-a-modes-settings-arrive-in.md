---
row: P4-28
baseline: 49aa659
created: 2026-10-02 09:37 UTC
modified: 2026-10-10 12:13 UTC
evidence:
  - claim: "A settings object of the right kind is handed straight back"
    source: "`command_translator.py` 330-331, and 261-262 for the plain single order"
  - claim: "A mapping is built into that kind"
    source: "`command_translator.py` 348-352"
  - claim: "Anything else refuses the command, barring the omission the plain single order allows"
    source: "`command_translator.py` 333-338, and 267-272 for the plain single order"
  - claim: "A key outside the kind's own fields refuses it rather than being dropped"
    source: "`command_translator.py` 340-346, and 274-281 for the plain single order"
  - claim: "The keys allowed are read off the kind's own fields once, as the module is loaded"
    source: "`command_translator.py` 82 and 139-144, built from the registries at 135-138"
  - claim: "A field that wants a tuple takes a list and is given a tuple"
    source: "`command_translator.py` 350, the fields found at 125-129"
  - claim: "Every mode has a settings kind registered, two of them sharing one"
    source: "`execution_params.py` 30-38"
  - claim: "The plain single order is the only kind that takes an omitted payload"
    source: "`command_translator.py` 264-265 against 333-338"
  - claim: "Omitting it leaves all three prices unset"
    source: "`single_shot_params.py` 30-32"
  - claim: "Where a mapping arrives it is also the only one testing each value itself, taking a decimal or nothing"
    source: "`command_translator.py` 283-297 against 348-352"
  - claim: "A settings object handed over whole skips that test"
    source: "`command_translator.py` 261-262"
  - claim: "A mode with no settings kind registered refuses the command"
    source: "`command_translator.py` 383-385"
---
# The payload a mode's settings arrive in

Each [way of working](ways-of-working-a-host-may-drive.md) has its own settings, and a [decision crossing into Praxis](how-a-decision-becomes-a-command.md) carries them as a payload. Turning that payload into the settings object the mode wants is the other half of the crossing.

## Three shapes

A payload that is already a settings object of the right kind is handed straight back. A mapping of field names is built into that kind. Anything else refuses the command, barring the omitted payload a plain single order allows.

A key outside the kind's own fields refuses it too, rather than being quietly dropped, so a strategy naming the wrong setting hears about it.

A field that wants a tuple takes a list and is given a tuple.

## Where the keys come from

The keys a mode allows are read off its settings kind's own fields, once, as the module is loaded. Registering a kind for a mode is all this translation needs — there is no second list of keys here to drift from the fields it would mirror.

Every mode has one registered, two of them sharing a kind. A mode with none would refuse the command.

## The plain single order apart

It is the only kind that takes an omitted payload: nothing becomes a settings object with all three of its prices left unset, which is [the shape a market order takes](the-prices-an-order-must-name.md).

Where a mapping arrives, it is also the only one testing each value where it is built, taking a decimal or nothing at all. The rest leave that to their own kinds. A settings object handed over whole skips the test either way.

## Related

- [How a decision becomes a command](how-a-decision-becomes-a-command.md)
- [Order types](order-types.md)
