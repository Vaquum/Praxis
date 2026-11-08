---
row: P65-04
baseline: 49aa659
created: 2026-11-12 23:30 UTC
modified: 2026-11-12 23:30 UTC
evidence:
  - claim: "An order carries a run of fills, which must hold something, and a name which is trimmed and refused where nothing is left"
    source: "`ledger.py` 495-496, then 498, then 500-501"
  - claim: "Every fill in the run is held to the same five tests a single fill is, the buy's fee test among them"
    source: "`ledger.py` 504-507, then 509-510, then 512-513, then 515-516, then 518-524"
  - claim: "One moment is worked out for the whole order and written into every fill of it"
    source: "`ledger.py` 526, used at 568"
  - claim: "A name the account has already recorded is refused, inside the lock and after the account is found"
    source: "`ledger.py` 529-530, then 534-537"
  - claim: "The movements of every fill are added onto the balances in turn and the pair weighed once, at the end"
    source: "`ledger.py` 539-545, then 547-551, then 553-557"
  - claim: "So a fill in the middle that would take a balance below nought passes where a later one brings it back"
    source: "`ledger.py` 542-545, adding without weighing"
  - claim: "Each fill takes a trade number of its own and the order takes one number for itself"
    source: "`ledger.py` 560-571, then 573-574"
  - claim: "The balances, the fills and the name are written together past both weighings, and the saving follows"
    source: "`ledger.py` 576-579, then 581"
---
# What an order settles as one

An order offered to [binsim's ledger](binsims-ledger.md) carries several fills and settles them as a single thing.

## What it must carry

A run of fills holding something, and a name which is trimmed and refused where nothing is left.

Every fill in the run is held to the same five tests [a single fill](the-order-a-fills-refusals-stand-in.md) is: all three figures finite, the price and the quantity above nought, the fee at or above it, and on a buy the fee below the quantity received.

## One moment for all of them

One moment is worked out for the whole order and written into every fill. So the fills of an order are indistinguishable by time, however long the venue took over them.

## The name already seen

Inside the lock, and after the account is found, a name the account has already recorded is refused. That is the one guard against the same order being settled twice.

## One weighing at the end

The movements of every fill are added onto the balances in turn, and the resulting pair is weighed once.

So a fill in the middle of the run that would take a balance below nought passes, where a later fill brings it back up. What is refused is a run whose total leaves a balance below nought — not a run that dips through it.

## The numbering

Each fill takes a trade number of its own, in the order it appears. The order takes one number for itself, after all of them.

## Writing

The balances, the fills and the name are written together past both weighings, and the saving follows. A refused order leaves all three as they were.

## Related

- [Binsim's ledger](binsims-ledger.md)
- [The order a fill's refusals stand in](the-order-a-fills-refusals-stand-in.md)
- [What settling a fill moves](what-settling-a-fill-moves.md)
