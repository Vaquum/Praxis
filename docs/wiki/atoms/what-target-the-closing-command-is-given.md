---
row: P184-01
baseline: 49aa659
created: 2026-11-16 12:30 UTC
modified: 2026-11-16 12:30 UTC
evidence:
  - claim: "The budget already recorded for the closing command is taken as its target where one stands"
    source: "`execution_manager.py` 7728, then 7729-7733"
  - claim: "The size being closed stands as the target where no budget is recorded"
    source: "`execution_manager.py` 7729-7733, the fallback at 7732"
  - claim: "The command built for the closing side is a plain market order carrying the entry's trade and timeout"
    source: "`execution_manager.py` 7735-7750, the target set at 7741"
  - claim: "An outcome whose filled figure stands above its target is refused outright"
    source: "`praxis/core/domain/trade_outcome.py` 130, then 131-132"
  - claim: "Both the protective pair's fills and the hand-placed close's are counted under that one command"
    source: "`execution_manager.py` 4927, and 7815, against 7865"
---
# What target the closing command is given

The command a hand-placed close settles under is given the whole position as its target, even where the close itself goes out for a part of it.

## Why not the remainder

A close can follow a protective pair that already filled part of the position, and the close goes out for what is left. Both those fills are counted under the one closing command.

An outcome whose filled figure stands above its target is refused outright. So a closing command targeting only the remainder would be handed more filled than it targeted, and its report could not be built at all.

## Where the target comes from

The budget already recorded for the closing command, where one stands. The size being closed, where none does.

So the figure is the one the admitted totals have been measured against all along, rather than a fresh reading of what is left.

## What else the command carries

A plain market order on the protective side, with the entry's own trade and timeout. Nothing of the entry's own way of working follows it.

## Related

- [What the closing side of a bracket is given](what-the-closing-side-of-a-bracket-is-given.md)
- [What a second budget offered for a command does](what-a-second-budget-offered-for-a-command-does.md)
- [How big a flatten goes out](how-big-a-flatten-goes-out.md)
