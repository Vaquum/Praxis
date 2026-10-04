---
row: P4-05
baseline: 49aa659
created: 2026-10-02 09:53 UTC
modified: 2026-10-04 11:43 UTC
evidence:
  - claim: "A Praxis outcome carries running totals for the command; a Nexus one carries one event's own figures"
    source: "`outcome_translator.py` 190-192 and 289-301"
  - claim: "A status outside the six handled raises"
    source: "`outcome_translator.py` 247-248"
  - claim: "A refusal makes one ending and the command is marked done"
    source: "`outcome_translator.py` 170-173"
  - claim: "A first waiting outcome makes an acknowledgement; a later one makes nothing"
    source: "`outcome_translator.py` 175-179"
  - claim: "A part-fill makes an acknowledgement first where none was sent, then a part-fill where the amount filled grew"
    source: "`outcome_translator.py` 194-210"
  - claim: "A full fill makes the acknowledgement where it is still needed, then a full fill where the amount grew, and marks the command done"
    source: "`outcome_translator.py` 212-225"
  - claim: "A cancellation or an expiry can make three: the acknowledgement, the part-fill accounting for the growth, and the ending"
    source: "`outcome_translator.py` 227-245"
  - claim: "Where the amount filled did not grow, the ending goes alone"
    source: "`outcome_translator.py` 228 and 243-244"
---
# How an outcome crosses back

Praxis reports what happened; Nexus keeps the books. The two [outcomes](what-an-outcome-is.md) are different shapes: Praxis's carries running totals for the whole command, Nexus's carries [one event's own figures](the-figures-carried-back-on-a-fill.md).

## How many come out

One Praxis outcome makes none, one, two or three Nexus ones, according to the status it carries.

A refusal makes one ending, and [an ending is the last of them](what-stops-an-outcome-crossing-twice.md). A first waiting outcome makes an acknowledgement; a second waiting outcome for the same command makes nothing.

A part-fill makes an acknowledgement first where none was sent, then a part-fill — but only where the amount filled actually grew. A full fill makes the acknowledgement where it is still needed, then a full fill where the amount grew, and marks the command done.

A [cancellation](how-a-trade-is-cancelled.md) or an expiry is where three can come out at once: the acknowledgement, the part-fill accounting for the growth, and the ending. Where the amount filled did not grow, the ending goes alone.

A status outside the six handled raises rather than passing something on.

## Related

- [What stops an outcome crossing twice](what-stops-an-outcome-crossing-twice.md)
- [The figures carried back on a fill](the-figures-carried-back-on-a-fill.md)
- [What an outcome is](what-an-outcome-is.md)
