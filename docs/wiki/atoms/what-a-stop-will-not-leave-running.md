---
row: P105-02
baseline: 49aa659
created: 2026-11-14 06:00 UTC
modified: 2026-11-14 06:00 UTC
evidence:
  - claim: "A stop on a facade that never started answers at once"
    source: "`praxis/trading.py` 652 into 653"
  - claim: "The stopping flag is raised before anything is torn down"
    source: "`praxis/trading.py` 655"
  - claim: "The reconciling task is cancelled, awaited with the cancelling alone suppressed, and let go"
    source: "`praxis/trading.py` 657-658, then 659-660, then 661"
  - claim: "The managed accounts are walked in sorted order, and an account the manager has lost is skipped"
    source: "`praxis/trading.py` 689, then 690-691 into 692-693"
  - claim: "The started flag is lowered and the loop let go only at the end of the work"
    source: "`praxis/trading.py` 798, then 799"
  - claim: "The stopping flag is lowered in a clause that runs however the stop ended"
    source: "`praxis/trading.py` 800-801"
  - claim: "A closing of one account's stream reports its own failure and goes no further"
    source: "`praxis/trading.py` 640 into 641-642, against 644-645 into 646-647"
---
# What a stop will not leave running

A stop cancels the reconciling loop, works through every managed account, and lowers its own flag however it ended.

## The two flags

A stop on a facade that never started answers at once. Otherwise the stopping flag is raised before anything is torn down — so [the loop sees it](how-the-reconciliation-loop-is-stopped.md) at its next account, and whatever else reads it knows a stop is under way.

The started flag is lowered and the loop let go only at the end of the work. The stopping flag is lowered in a clause that runs however the stop ended.

So during a stop the facade reports itself started and stopping at once, and after a failed stop it reports itself started and not stopping — because the lowering of the one is guaranteed and the lowering of the other is not.

## The loop

Cancelled, awaited with the cancelling alone suppressed, and let go. Any other failure of that task travels out of the stop.

## The accounts

Walked in sorted order. An account the manager has lost is skipped rather than failing the stop.

## One stream at a time

A closing of one account's stream reports its own failure and goes no further, so one stream that will not close cannot stop the others being closed.

## Related

- [What a failed start undoes](what-a-failed-start-undoes.md)
