---
row: N5-06
baseline: 49aa659
created: 2026-10-25 14:00 UTC
modified: 2026-10-25 14:00 UTC
evidence:
  - claim: "A sale a host sends as it stops carries a decision allowing it, rather than asking the walk for one"
    source: "`nexus/startup/shutdown_sequencer.py` 398-404"
  - claim: "The walk is asked where a strategy submits in the ordinary way"
    source: "`nexus/strategy/action_submit.py` 242"
  - claim: "So the stages that walk names see nothing of the shutdown sale, among them the one refusing a sale larger than the position less what is pending on it"
    source: "`nexus/core/validator/pipeline_models.py` 50-56, the walk reached from `nexus/strategy/action_submit.py` 242, the cap at `nexus/core/validator/intake_stage.py` 278-284"
  - claim: "A sale going out in one shot and asking for the market price is weighed once it arrives, and refused where its slippage against the book is too wide and a limit on that slippage is set"
    source: "`praxis/core/execution_manager.py` 4009 into 4230-4240, the weighing at 4066-4098 and the two ways past it at 4064-4065"
  - claim: "A sale asking to be fed out instead takes another road and never reaches that weighing, its own slices going out unweighed by it"
    source: "`praxis/core/execution_manager.py` 3994-3998 into 5908 and 5953-5990"
  - claim: "Which road it takes is the mode the strategy asked for, and one shot where it asked for none"
    source: "`nexus/infrastructure/praxis_connector/translate.py` 96-101, the mode stood in at 27"
  - claim: "Whether it asks for the market price is a separate answer, the market price standing in only where the strategy named no kind of order"
    source: "`nexus/infrastructure/praxis_connector/translate.py` 101-103, the type stood in at 28"
  - claim: "The venue adapter reads it for the venue's own sizes as the order is placed, refusing one below the smallest amount the venue takes, and passing it unread where it has no filters for that symbol"
    source: "`praxis/infrastructure/binance_adapter.py` 1520 into 1200-1204, the passing at 1190-1192"
---
# What weighs a shutdown sale

[A sale a host sends as it stops](the-sale-a-host-sends-as-it-stops.md) skips the checks a strategy's own sale passes, and meets two the host applies later.

## What it skips

It carries a decision allowing it rather than asking [the walk](the-checks-a-decision-passes.md) for one, and the walk is asked where a strategy submits in the ordinary way. So the stages that walk names see nothing of it, [the cap on selling the same holding twice](what-a-pending-sale-refuses.md) among them.

## What still weighs it

The host's own guard, on the road a sale going out in one shot takes. Slippage against the book that is too wide is refused there, shutdown or not — where the sale asks for the market price and a limit on that slippage is set. A sale of any other kind, or one sent where no limit is set, passes the guard unweighed.

A sale asking instead to be fed out takes another road and never reaches that weighing. Which road it takes is the mode the strategy asked for, and one shot where it asked for none. Whether it asks for the market price is a separate answer: the market price stands in only where the strategy named no kind of order, so a sale sent in one shot as any other kind passes the guard unweighed.

The venue adapter reads it for the venue's own sizes as the order is placed, and refuses one below the smallest amount the venue takes — unless it has no filters for that symbol, in which case it passes the order unread.

## Related

- [The sale a host sends as it stops](the-sale-a-host-sends-as-it-stops.md)
- [The roads around the checks](the-roads-around-the-checks.md)

---

Created 2026-10-25 14:00 UTC · Last modified 2026-10-25 14:00 UTC
