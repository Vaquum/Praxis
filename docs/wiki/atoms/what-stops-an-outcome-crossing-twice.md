---
row: P4-30
baseline: 49aa659
created: 2026-10-02 10:10 UTC
modified: 2026-10-04 11:43 UTC
evidence:
  - claim: "Once an ending has been made, later outcomes for that command are dropped"
    source: "`outcome_translator.py` 156-164, the name kept at 257"
  - claim: "Ten thousand ended commands are remembered by default, and that number can be set"
    source: "`outcome_translator.py` 259-260 against the number kept at 133, defaulted at 80"
  - claim: "The oldest name goes when a further command ends, so it is ending commands rather than passing time that forgets one"
    source: "`outcome_translator.py` 257-260"
  - claim: "A duplicate passed on after forgetting has nothing applied for it only where its own name went through before"
    source: "Nexus `outcome_processor.py` 130-140, the names kept at 163-165"
  - claim: "A full fill adding nothing makes no full-fill leg, so that name is new when it comes round again"
    source: "`outcome_translator.py` 216-223 within 212-225"
  - claim: "Each crossing outcome is named from the account, the command and which leg it is, with a number on successive part-fills"
    source: "`outcome_translator.py` 388-390"
  - claim: "Both names are written down with the outcome and read back from there"
    source: "`execution_manager.py` 10818-10831 and `launcher.py` 1680-1684"
  - claim: "Replaying the written record in order rebuilds the same names, the record being read oldest first"
    source: "`launcher.py` 1749-1776, reading at `event_spine.py` 189-191"
---
# What stops an outcome crossing twice

Once an ending has been made for a command, later outcomes bearing its name are dropped before they can [cross back](how-an-outcome-crosses-back.md). Two things hold that: a memory of ended commands, and a name a crossing outcome gets the same way every time.

## The memory

Ten thousand such names are remembered by default, and the oldest goes when a further command ends — so it is ending commands, rather than passing time, that forgets one.

A duplicate passed on after that has nothing applied for it only where its own name went through before. A name the far end has never seen is new to it — which a full fill can be, where the fill that completed the command added nothing to the amount and so made no full-fill leg to be named.

## The names

Each crossing outcome is named from the account, the command and which leg it is, with a number on successive part-fills. Both names are written down with the outcome and read back from there, so replaying the written record in order rebuilds the same names.

## Related

- [How an outcome crosses back](how-an-outcome-crosses-back.md)
- [Where duplicates stop](where-duplicates-stop.md)
