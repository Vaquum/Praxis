---
row: N4-05
baseline: 49aa659
created: 2026-10-23 13:30 UTC
modified: 2026-10-23 13:30 UTC
evidence:
  - claim: "A close the venue refuses before an order exists is written off as dust only where the position has nothing pending on it"
    source: "`praxis/launcher.py` 1323 and 1339-1342 into 1363-1367, ending at 1369, the dust itself at `nexus/infrastructure/praxis_connector/outcome_processor.py` 696-702"
  - claim: "The fill road asks nothing about the figure: it takes the fill's own size off and then weighs only the outcome, the intent and what is left"
    source: "`nexus/infrastructure/praxis_connector/outcome_processor.py` 560 before 562-566"
  - claim: "So a finishing fill of a close meant to take the whole position writes the remainder off whatever the figure then reads, which the fill may have left standing or cleared"
    source: "`nexus/infrastructure/praxis_connector/outcome_processor.py` 560 and 562-566 into 576-580"
  - claim: "The position is removed with it, a size of nought being what closes it, so nothing is left for a start to set to nought"
    source: "`nexus/infrastructure/praxis_connector/outcome_processor.py` 594-595 with `nexus/core/domain/position.py` 94, against `nexus/core/capital_controller/capital_controller.py` 214-217 and 233"
  - claim: "A cancel and a refusal each take their own amount off the figure, as a fill does, and clear it where that amount is the whole of it"
    source: "`nexus/infrastructure/praxis_connector/outcome_processor.py` 336-342 and 307-310, both into 610"
---
# What a pending sale does to the dust

[A pending sale](what-a-pending-sale-is.md) shuts one of the two roads into [the dust](where-a-positions-last-scraps-go.md) and leaves the other open.

## The road it shuts

A close the venue refuses before an order exists is written off as dust only where the position has nothing pending on it. A resting sale therefore holds that road shut, and holds it shut until the figure reaches nought. A fill, a cancel and a refusal each take their own amount off it; whether that empties it depends on what else is out against the position.

## The road it leaves open

The fill road asks nothing about the figure. It takes the fill's own size off the pending figure first, and then weighs only three things: that the outcome is a finishing fill, that the close was meant to be whole, and that something is left.

So a finishing fill of a close meant to take the whole position, leaving part of it behind, writes that part off whatever the figure then reads. The fill may have cleared it, or left some of it standing — the road is taken either way.

The position goes with the remainder — a size of nought is what closes it — so a figure left standing goes with it too: there is nothing there for a start to find and set to nought.

## Related

- [What a pending sale is](what-a-pending-sale-is.md)
- [Where a position's last scraps go](where-a-positions-last-scraps-go.md)

---

Created 2026-10-23 13:30 UTC · Last modified 2026-10-23 13:30 UTC
