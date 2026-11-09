---
row: P87-02
baseline: 49aa659
created: 2026-11-13 20:30 UTC
modified: 2026-11-13 20:30 UTC
evidence:
  - claim: "A ledger refuses to be built without an account name"
    source: "`account_ledger.py` 70 into 71-72"
  - claim: "Every balance starts at nought, one for each kind of account there is"
    source: "`account_ledger.py` 76"
  - claim: "The trades, the journal and the open lots all start empty, and the ledger starts unregistered"
    source: "`account_ledger.py` 77, and 78, and 79, and 80"
  - claim: "A fill for any symbol but the one it books raises as something not built"
    source: "`account_ledger.py` 244 into 245-246"
  - claim: "A sell larger than the lots left open raises, naming how much was left over"
    source: "`account_ledger.py` 376-377, reached where the walk at 364 runs out"
  - claim: "The walk over the lots runs while something remains and lots are there, from a lookup that may find none at all"
    source: "`account_ledger.py` 360, then 361-362, then 364, the cost answered at 379"
---
# What the ledger refuses

The ledger refuses three things: a build with no account name, a fill in any other symbol, and a sell larger than what it has open.

## The name

A ledger refuses to be built without an account name. Nothing else about the name is asked.

## What it starts holding

Every balance starts at nought, one for each kind of account there is. The trades, the journal and the open lots all start empty, and the ledger starts unregistered.

## The one symbol

A fill for any symbol but the one it books raises as something not built, rather than as a bad request. So the refusal says the ledger cannot do this at all, not that this fill was wrong.

## The sell it cannot cover

The walk over the lots runs while something remains and lots are there, from a lookup that may find none at all. A sell larger than the lots left open raises, naming how much was left over.

Because the lookup can find nothing, a sell against a trade with no lots at all raises the same way as one against a trade with too few — and the figure in the refusal is the whole quantity asked for.

## Related

- [How a journal entry moves the balances](how-a-journal-entry-moves-the-balances.md)
