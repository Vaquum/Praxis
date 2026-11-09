---
row: P54-01
baseline: 49aa659
created: 2026-11-08 17:53 UTC
modified: 2026-11-09 05:30 UTC
evidence:
  - claim: "An event naming another account raises before the lock is taken"
    source: "`account_ledger.py` 97-99, ahead of 101"
  - claim: "Inside the lock, a registration is answered first of all"
    source: "`account_ledger.py` 103-106"
  - claim: "Anything else arriving before a registration raises"
    source: "`account_ledger.py` 108-110"
  - claim: "A second registration raises, the way of costing being settled once"
    source: "`account_ledger.py` 235-237"
  - claim: "A fill naming any other trading pair raises as something the ledger does not do"
    source: "`account_ledger.py` 244-246, reached from 112-113"
  - claim: "A closing naming a trade the ledger holds nothing for passes through silently"
    source: "`account_ledger.py` 259-262, reached from 115-116, the one other road taken at 118-119"
---
# What the ledger refuses to apply

[The money ledger](the-money-ledger.md) books one account, and the refusals it makes stand in an order a reader has to keep.

## Outside the lock

One refusal comes before the lock is taken: an event naming another account. So a misrouted event never waits behind the work of the account it was misrouted to.

## Inside it, in order

A registration is answered first of all, which is how a ledger's first event can be one.

Anything else arriving before a registration raises. A second registration raises too: the way of costing a sell is settled once and cannot be changed.

Only past those does a fill reach the test of its trading pair, which refuses any pair but the one as something the ledger does not do — so a fill naming another pair for an unregistered ledger is refused on the registration, its pair never looked at.

## The event answered by silence

A closing naming a trade the ledger holds nothing for passes through silently: no refusal, no record. Like the others it is reached only past the refusals above, so the silence belongs to a registered ledger reading a closing whose trade it holds nothing for.

## Related

- [The money ledger](the-money-ledger.md)
- [Lots and what a sell costs](lots-and-what-a-sell-costs.md)
- [What a rebuilt ledger carries](what-a-rebuilt-ledger-carries.md)
