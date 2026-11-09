---
row: P100-01
baseline: 49aa659
created: 2026-11-14 03:30 UTC
modified: 2026-11-14 03:30 UTC
evidence:
  - claim: "The loop runs while the stopping flag is clear"
    source: "`praxis/trading.py` 1351"
  - claim: "Its wait between cycles stands inside a guard naming the cancelling alone, which answers rather than carrying on"
    source: "`praxis/trading.py` 1352-1353 into 1354, then 1355"
  - claim: "The ready accounts are walked in sorted order, so the order is the same every cycle"
    source: "`praxis/trading.py` 1357"
  - claim: "The stopping flag is weighed again before each account, and answers there where it is set"
    source: "`praxis/trading.py` 1358 into 1359"
  - claim: "Each account's turn is then awaited one at a time"
    source: "`praxis/trading.py` 1361"
---
# How the reconciliation loop is stopped

The loop that reconciles each account can be stopped two ways, and the difference is how long the stop takes to land.

## The flag, weighed twice

Once before each cycle, and again before each account inside it. So a stop set while the loop is partway through its accounts lands before the next account rather than after the cycle.

The second weighing is what makes the stop quick. Without it, a stop during a cycle over many accounts would wait for all of them.

## The cancelling

The wait between cycles stands inside a guard naming the cancelling alone. A cancelled wait answers rather than carrying on, so cancelling the task ends the loop at the point it was idling.

A cancelling that arrives while an account is being reconciled is not caught here. It travels out of whatever that account's turn was doing.

## The order

The ready accounts are walked in sorted order, so the order is the same every cycle. Each account's turn is awaited one at a time, so a slow account delays the ones after it within that cycle.

## Related

- [What the phase map and the gate agree on](what-the-phase-map-and-the-gate-agree-on.md)
