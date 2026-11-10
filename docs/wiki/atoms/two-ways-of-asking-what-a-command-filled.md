---
row: P142-01
baseline: 49aa659
created: 2026-11-09 11:05 UTC
modified: 2026-11-09 11:05 UTC
evidence:
  - claim: "The admitted totals for a command are read from a mapping the account keeps, and answered as they stand where any are held"
    source: "`execution_manager.py` 2588, then 2590 into 2591"
  - claim: "Where none are held the raw projected totals are read instead, and either of them standing above nothing is weighed"
    source: "`execution_manager.py` 2593, then 2595"
  - claim: "Nothing filled is answered in that case whatever the raw totals said"
    source: "`execution_manager.py` 2608, past 2595-2606"
  - claim: "The delivered amount is worked out from those same raw totals"
    source: "`execution_manager.py` 2638, reading what 2593 reads"
  - claim: "Every order of that command, live and closed alike, has its base-asset fee added up"
    source: "`execution_manager.py` 2639, then 2641-2644, then 2645 into 2646"
  - claim: "The delivered amount is the filled amount less that total fee"
    source: "`execution_manager.py` 2648"
---
# Two ways of asking what a command filled

A command's filled amount can be asked for in two ways, and the two answer different figures from different places.

## What was admitted

Read from a mapping the account keeps, and answered as it stands where anything is held there.

Where nothing is held, the raw projected totals are read, and either of them standing above nothing is weighed — that being a fill which reached the ledger without passing through the admission that caps it.

Nothing filled is then answered regardless of what those raw totals said. So the road fails closed: it would rather report nothing than report an uncapped figure.

## What was delivered

Worked out from those same raw totals — the very figure the first road refuses to report.

Every order of that command, live and closed alike, has its base-asset fee added up, and the delivered amount is the filled amount less that total.

So "delivered" means what actually arrived after the venue took its fee in the thing being bought, where "admitted" means what the accounting allowed to count.

## Where the two part

One is capped and may read as nothing while fills exist. The other is uncapped and net of fees. A caller asking "how much filled?" gets a different number depending on which it asks, and only one of the two will tell it that something is wrong.

## Related

- [The part of a fill a command counts](the-part-of-a-fill-a-command-counts.md)
- [What a fee figure is worked out from](what-a-fee-figure-is-worked-out-from.md)
- [What a fill changes](what-a-fill-changes.md)
