---
row: P180-02
baseline: 49aa659
created: 2026-11-16 10:30 UTC
modified: 2026-11-16 12:30 UTC
evidence:
  - claim: "The bracket is marked as having had its protection placed before anything is sent"
    source: "`execution_manager.py` 4906, then 4925, then 4929-4935"
  - claim: "That mark is what the boot's own pass over brackets reads to pass one over"
    source: "`execution_manager.py` 4906, against 4739, then 4740"
  - claim: "The protective side is the opposite of the entry's"
    source: "`execution_manager.py` 4909-4911"
  - claim: "The three prices are worked out from the entry's average price"
    source: "`execution_manager.py` 4912-4914"
  - claim: "The closing side gets a command name of its own, and the pair an order name with a fixed place"
    source: "`execution_manager.py` 4915, then 4916-4920"
  - claim: "A command of its own is built for the closing side, and a budget recorded against it"
    source: "`execution_manager.py` 4921-4924, then 4927"
  - claim: "The intent names the closing command rather than the entry's"
    source: "`execution_manager.py` 4929-4935, the command named at 4932"
---
# What the closing side of a bracket is given

Putting a protective pair up for a filled entry gives the closing side of the trade its own command, its own name and its own budget, so what it fills is counted apart from the entry.

## Its own everything

A command name of its own, worked out from the entry's. An order name for the pair, with a fixed place so the name is the same each time it is worked out. A command of its own, built for the protective side. And a budget recorded against that command.

The intent names the closing command rather than the entry's, which is what keeps the pair's fills out of the entry's totals.

## What the pair is made of

The protective side is the opposite of the entry's — a long is closed by selling, a short by buying. The three prices are worked out from the entry's average price.

## The mark that comes first

The bracket is marked as having had its protection placed before anything is sent. That mark is what the boot's own pass over brackets reads to pass one over, so a send that fails leaves the mark set and that pass does not try again.

## Related

- [Protection](protection.md)
- [What a restart puts back of a bracket](what-a-restart-puts-back-of-a-bracket.md)
- [What a second budget offered for a command does](what-a-second-budget-offered-for-a-command-does.md)
