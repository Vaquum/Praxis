---
row: N3-04
baseline: 49aa659
created: 2026-10-22 15:30 UTC
modified: 2026-10-22 17:00 UTC
evidence:
  - claim: "Three running totals are each set to nought where they stand above it, and each one is logged as it goes"
    source: "`nexus/core/capital_controller/capital_controller.py` 193-212"
  - claim: "A total already at nought is left alone and logged not at all"
    source: "`nexus/core/capital_controller/capital_controller.py` 193, 200 and 207"
  - claim: "The reservations and orders behind the three are made empty as the controller is built, so a start has none of them"
    source: "`nexus/core/capital_controller/capital_controller.py` 108 and 110"
  - claim: "The pass refuses to run at all where either is no longer empty"
    source: "`nexus/core/capital_controller/capital_controller.py` 182-188"
  - claim: "What is left uncommitted is the pool less the three and two figures besides, so clearing the three raises it"
    source: "`nexus/core/domain/capital_state.py` 109-115"
  - claim: "It asks the venue nothing: no call to it is made anywhere in the pass"
    source: "`nexus/core/capital_controller/capital_controller.py` 181-273"
  - claim: "What the three totals came to does not decide what follows, the positions being taken up next whatever they held"
    source: "`nexus/core/capital_controller/capital_controller.py` 214 after 193-212"
---
# What a boot finds stranded

Stranded money is an amount the last run counted as committed with nothing left to release it, and a boot writes it off.

## The three totals

Money set aside, money with an order in flight, and money with an order working are each kept as one running total. The reservations and orders behind them are made empty as the controller is built, so a start has none of them to work from.

Each total standing above nought is set to nought and logged. One already at nought is left alone and not logged, so a start that finds all three at nought writes none of these three lines — it goes on to [the positions](what-a-boot-rebuilds-from-the-positions.md) either way.

The pass refuses to run at all where a reservation or an order is no longer empty.

## What it does not ask

It asks the venue nothing — no call to it is made anywhere in the pass. The money is counted as free again on the strength of the record alone.

## Related

- [How Nexus sets money aside](how-nexus-sets-money-aside.md)
- [What a boot rebuilds from the positions](what-a-boot-rebuilds-from-the-positions.md)

---

Created 2026-10-22 15:30 UTC · Last modified 2026-10-22 17:00 UTC
