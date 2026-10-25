---
row: N4-02
baseline: 49aa659
created: 2026-10-23 11:10 UTC
modified: 2026-10-25 09:00 UTC
evidence:
  - claim: "A pending sale is written onto the position as the sale is sent, by the size of that order, through the registration the host runs for it"
    source: "`praxis/launcher.py` 2159-2164, reached from `nexus/strategy/action_submit.py` 313-337"
  - claim: "Which of the two writes it is decided by whether a registration came back, Nexus writing it on its own side where none did"
    source: "`nexus/strategy/action_submit.py` 420 against 431-436"
  - claim: "A host shutting down writes it the same way for a sale it sends on the way out, and where building the record of that sale fails the sale has gone out with nothing written against it"
    source: "`nexus/startup/shutdown_sequencer.py` 407 before 432-443, against 458 with the size at 561"
  - claim: "A fill takes its own size off, never below nought"
    source: "`nexus/infrastructure/praxis_connector/outcome_processor.py` 560"
  - claim: "A cancel takes off the smaller of two figures: what the report says was left of the order, and the size the order was sent with; the figure is floored at nought"
    source: "`nexus/infrastructure/praxis_connector/outcome_processor.py` 336-342 into 610"
  - claim: "What was left is the target the host recorded less what filled, and where the host recorded no target it is left out, so the size sent with stands alone and after a part-fill takes off more than the order still had pending"
    source: "`praxis/outcome_translator.py` 348-351 into `nexus/infrastructure/praxis_connector/outcome_processor.py` 336-341, against 560"
  - claim: "A refusal takes off the size the order was sent with"
    source: "`nexus/infrastructure/praxis_connector/outcome_processor.py` 307-310 into 610"
  - claim: "A start sets it to nought outright"
    source: "`nexus/core/capital_controller/capital_controller.py` 233"
  - claim: "A sale larger than the position less what is pending on it is refused at the intake stage"
    source: "`nexus/core/validator/intake_stage.py` 278-284"
  - claim: "An acknowledgement of a sale returns before any figure is touched"
    source: "`nexus/infrastructure/praxis_connector/outcome_processor.py` 190-195"
---
# What a pending sale is

A pending sale is how much of a position already has a sale out against it.

## Written on

It is written onto the position as the sale is sent, by the size of that order: through the registration the host runs for it, or on Nexus's own side where no registration came back. A host shutting down writes it the same way for a sale it sends on the way out — and where building the record of that sale fails, the sale has already gone out with nothing written against it.

## Taken off

The fill that answers the sale takes its own size off, never below nought. A cancel takes off the smaller of two figures: what the report says was left — the target the host recorded, less what filled — and the size the order was sent with. A refusal takes off the size sent with. Both floor at nought. Where the host recorded no target, the size sent with stands alone, which after a part-fill is more than the order still had pending. A start sets the figure to nought outright.

## What it refuses

A sale larger than the position less what is already pending is [refused at the intake stage](what-a-pending-sale-refuses.md).

## While the order is alive

An acknowledgement of a sale returns before any figure is touched, so the pending figure stands while the order is alive — which is right. What that figure does to [the roads into the dust](what-a-pending-sale-does-to-the-dust.md) is a question of its own.

## Related

- [Where a position's last scraps go](where-a-positions-last-scraps-go.md)
- [What a boot rebuilds from the positions](what-a-boot-rebuilds-from-the-positions.md)

---

Created 2026-10-23 11:10 UTC · Last modified 2026-10-25 09:00 UTC
