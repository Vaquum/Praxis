---
row: P87-01
baseline: 49aa659
created: 2026-11-09 05:30 UTC
modified: 2026-11-09 05:30 UTC
evidence:
  - claim: "A buy's entry is built with no realized figure, where a sell's comes back with one"
    source: "`account_ledger.py` 248 into 249-250, or 252 into 253"
  - claim: "Both roads then post the same way, by the one routine"
    source: "`account_ledger.py` 255"
  - claim: "Posting puts the entry on the journal before any balance moves"
    source: "`account_ledger.py` 405, ahead of 407-409"
  - claim: "Each line moves its account by the debit less the credit where that account is debit-normal, and by the credit less the debit otherwise"
    source: "`account_ledger.py` 408, applied at 409"
  - claim: "Posting also adds the realized figure and the fee to the trade's own record, made the first time that trade is seen"
    source: "`account_ledger.py` 413, then 415, then 416-417"
  - claim: "Every entry is built carrying the moment of the fill it came from"
    source: "`account_ledger.py` 395-396"
  - claim: "A buy's entry debits the coin account and credits the cash account by the same notional"
    source: "`account_ledger.py` 292 into 293-295, answered at 318"
---
# How a journal entry moves the balances

Every fill the ledger books becomes one journal entry, and posting that entry is what moves the balances.

## The two roads in

A buy's entry is built with no realized figure. A sell's comes back with one. Both roads then post the same way, by the one routine — so whatever differs between a buy and a sell is settled before the posting, never inside it.

## The order of posting

The entry goes on the journal before any balance moves. A journal and a set of balances that disagree can therefore only disagree one way: the entry is there and the balances have yet to move.

## The sign each line takes

Each line moves its account by the debit less the credit where that account is debit-normal, and by the credit less the debit otherwise. So the same pair of figures moves two accounts in opposite directions, and which direction is a property of the account rather than of the entry.

A buy's entry debits the coin account and credits the cash account by the same notional.

Every entry is built carrying the moment of the fill it came from, so the journal's order is the fills' order and not the posting's.

## What posting also does

It adds the realized figure and the fee to the trade's own record, made the first time that trade is seen. So the trade records are a second tally kept alongside the balances, from the same posting.

## Related

- [What the ledger refuses](what-the-ledger-refuses.md)
