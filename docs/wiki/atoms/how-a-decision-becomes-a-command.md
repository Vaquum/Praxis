---
row: P4-04
baseline: 49aa659
created: 2026-10-02 09:35 UTC
modified: 2026-10-04 16:30 UTC
evidence:
  - claim: "A new order crossing into Praxis through the launcher has five of its fields re-keyed and its settings converted where needed"
    source: "`launcher.py` 441-451, installed at 453-455 and called from Nexus `praxis_outbound.py` 157-182"
  - claim: "A Praxis check that tests a field against its own copy refuses one of Nexus's"
    source: "`validate_trade_command.py` 189-200, against the two copies at `enums.py` 66-68 and 118-119 and Nexus `order_types.py` 15-37"
  - claim: "A field already of the Praxis kind is handed straight back"
    source: "`command_translator.py` 158-159"
  - claim: "Otherwise the string it carries is read, and the Praxis kind built from that string"
    source: "`command_translator.py` 160, 167 and 169"
  - claim: "Something carrying no string refuses the command"
    source: "`command_translator.py` 161-166"
  - claim: "A string with no Praxis equivalent refuses it too"
    source: "`command_translator.py` 170-175"
  - claim: "One pair of kinds does not share its strings, and a small table records which means which"
    source: "`command_translator.py` 146-150, consulted at 167 and passed in at 234"
  - claim: "An omitted maker preference becomes no preference, which is read the same way as having none"
    source: "`command_translator.py` 212-213, read at `validate_trade_command.py` 260-268"
  - claim: "An omitted self-trade setting becomes none, which nothing downstream weighs"
    source: "`command_translator.py` 232-233, the value only carried at `execution_manager.py` 5176"
  - claim: "An ordinary new order from Nexus carries that setting from its account's own configuration"
    source: "Nexus `translate.py` 125, held to a real value at `instance_config.py` 229-231"
  - claim: "The same translation is done for a change already under way, over two fields"
    source: "`launcher.py` 419-427"
---
# How a decision becomes a command

Nexus decides what to do; Praxis carries it out. In between, a new order crossing through the launcher is turned into a [command](what-a-trade-is.md): five of its fields are re-keyed, and [its settings converted](the-payload-a-modes-settings-arrive-in.md) where they need it.

## Why re-keying is needed

Nexus and Praxis each keep their own copy of the same five lists of names — which side an order is, what kind it is, how it is to be carried out, whether it should wait to be matched, and what to do when it meets itself.

Agreeing on the strings is not enough. Each copy is a separate thing to Python, so a Praxis check that tests a field against its own copy refuses one of Nexus's. Each field is therefore read for its string and rebuilt from that string as Praxis's own.

A field that already is of the Praxis kind is handed straight back.

## Where it refuses

Something carrying no string at all refuses the command. So does a string with no equivalent on the Praxis side.

## The two that need help

One pair of lists does not share its strings — Nexus says cancel where Praxis says expire — so a small table records which means which, and the translation reads it rather than dropping the value.

Two fields may arrive omitted. No maker preference becomes no preference, which the check downstream reads the same way as having none at all. No self-trade setting becomes none — a value nothing downstream weighs, and one an ordinary new order carries from its account's configuration rather than omitting.

The same translation runs for [a change to work already sent](changing-work-already-sent.md), over two of its fields.

## Related

- [The payload a mode's settings arrive in](the-payload-a-modes-settings-arrive-in.md)
- [Trades, requests and orders](what-a-trade-is.md)
