---
row: N15-08
baseline: 49aa659
created: 2026-11-09 14:00 UTC
modified: 2026-11-10 21:00 UTC
evidence:
  - claim: "The moment a mode last changed is asked for nothing beyond being a moment"
    source: "`nexus/core/domain/operational_mode.py` 151-153"
  - claim: "Its own default is the earliest moment there is, which carries no zone"
    source: "`nexus/core/domain/operational_mode.py` 138"
  - claim: "The moment a hold was placed is asked the same and no more"
    source: "`nexus/core/domain/operational_mode.py` 52-54"
  - claim: "The moment the rolling loss windows are measured back from must carry a zone whose offset for it is something, and is asked no more than that"
    source: "`nexus/infrastructure/loss_derivation.py` 80-85"
  - claim: "The records this side sends and receives are held to the universal-time marker itself"
    source: "`nexus/infrastructure/praxis_connector/trade_command.py` 133-135, or `nexus/infrastructure/praxis_connector/trade_outcome.py` 108-110, or `nexus/core/capital_controller/reservation.py` 70-72"
---
# The moments with no marker

Two moments in the records holding the mode are asked for nothing beyond being moments.

## The two

The moment a mode last changed, and the moment a hold was placed. Each must be a moment, and that is the whole of what is asked: no zone is demanded, so one carrying none is kept.

The first carries a default of its own — the earliest moment there is, which has no zone — so a mode state built without one holds a naive moment from the start.

## What stands around them

[The instruction this side sends](the-marker-a-commands-moment-must-carry.md), the report it gets back, and the record of money held are each refused unless their moment carries the universal-time marker itself. A zone merely standing at that offset is not enough for them.

Between the two stands a third rule. The moment the rolling loss windows are measured back from must carry a zone, and that zone must give an offset for that moment; nothing more is asked, so a moment at an offset of its own is kept where the records crossing the seam would turn it back.

So two moments inside the mode are held to a weaker rule than the moments crossing the seam, and a reader comparing one of them against a moment from across the seam is comparing one that may carry no zone with one that must.

## Related

- [What the records of the mode refuse](what-the-records-of-the-mode-refuse.md)
- [The marker a command's moment must carry](the-marker-a-commands-moment-must-carry.md)
