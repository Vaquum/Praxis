---
row: P7-04
baseline: 49aa659
created: 2026-11-09 07:30 UTC
modified: 2026-11-09 07:30 UTC
evidence:
  - claim: "A bracket's protective exit is named by joining one letter to the entry's name with a dash"
    source: "`praxis/core/bracket_exit_command_id.py` 31, the letter at 17"
  - claim: "Nothing is asked of the name handed in, so an empty one yields a name that is a dash and that letter"
    source: "`praxis/core/bracket_exit_command_id.py` 31, the one statement the function has, which tests it nowhere"
  - claim: "Callers in both the launcher and the manager work the name out by calling this one helper"
    source: "`praxis/launcher.py` 1574 and 1620, and `praxis/core/execution_manager.py` 4915 and 7234"
  - claim: "Nothing in the Nexus checkout works the name out"
    source: "`praxis/core/bracket_exit_command_id.py` 31, with no statement in the Nexus checkout deriving it"
  - claim: "The derived name is put on the note for the protective exit, and that note is handed to the Nexus side with the outcome"
    source: "`praxis/launcher.py` 1578-1579, handed over at 2919, where `nexus/infrastructure/praxis_connector/outcome_processor.py` 142 reads the name off it"
---
# The name a bracket's protective exit is given

A bracket's protective exit is named by joining one letter to the entry's name with a dash.

## The derivation

One statement does it, and nothing is asked of the name handed in. An empty one yields a name that is a dash and that letter.

Callers in both the launcher and the manager work the name out by calling this one helper, so no two of them can drift apart.

## Where it is worked out

Nothing in the Nexus checkout works it out. The letter and the joining appear in Praxis alone, The derived name is put on the note for the protective exit, and that note is handed to the Nexus side along with the outcome, which reads the name off it. So the other side reads a name it was given rather than one it worked out.

## Related

- [Protection](protection.md)
- [What a restart puts back of a bracket](what-a-restart-puts-back-of-a-bracket.md)
