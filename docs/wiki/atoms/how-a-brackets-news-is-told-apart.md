---
row: P153-01
baseline: 49aa659
created: 2026-11-09 11:56 UTC
modified: 2026-11-09 11:56 UTC
evidence:
  - claim: "News that is none of a fill, a cancellation, an expiry or a rejection is dropped"
    source: "`execution_manager.py` 4660-4662 into 4663"
  - claim: "The order is looked for among the live orders and then among the closed ones, and news naming neither is dropped"
    source: "`execution_manager.py` 4665-4668, then 4669 into 4670"
  - claim: "An order whose status is not terminal is dropped too, so only an ended order reaches anything"
    source: "`execution_manager.py` 4672 into 4673"
  - claim: "A leg's news is turned into its parent list's name, and an order that is no leg stands for itself"
    source: "`execution_manager.py` 4680-4682"
  - claim: "The brackets are searched for one whose protection carries that name and reports itself active"
    source: "`execution_manager.py` 4683-4691"
  - claim: "A match sends the news down the protection's own road and the pass ends"
    source: "`execution_manager.py` 4693 into 4694, then 4696"
  - claim: "Otherwise the bracket is looked up by the order's command, and news that is neither that bracket's nor its entry's is dropped"
    source: "`execution_manager.py` 4698, then 4699 into 4700"
  - claim: "The bracket is taken out of the account's brackets before its entry is settled"
    source: "`execution_manager.py` 4702, ahead of 4714-4717"
  - claim: "An entry that ended having filled nothing is reported and left without protection"
    source: "`execution_manager.py` 4704 into 4712"
---
# How a bracket's news is told apart

A bracket hears about two quite different orders — its entry and its protection — and the same news handler tells them apart by searching for the protection first.

## The three drops

News of the wrong kind. News naming an order found in neither the live orders nor the closed ones. And an order whose status is not terminal — so only an ended order reaches anything here.

Looking in the closed orders as well as the live ones is what lets news arrive after the order has been moved aside.

## Finding the protection

A leg's news is turned into its parent list's name, and an order that is no leg stands for itself. The brackets are then searched for one whose protection carries that name and reports itself active.

A match sends the news down the protection's own road, and the pass ends there. So the protection is tried before the entry is even considered.

## Finding the entry

Otherwise the bracket is looked up by the order's command, and news that is neither that bracket's nor its own entry's is dropped.

The bracket is then taken out of the account's brackets **before** its entry is settled — so [placing the protection](what-placing-a-brackets-protection-writes-first.md) puts it back, and a failure in between leaves no bracket at all.

## The entry that filled nothing

Reported, and left without protection. Its bracket has already been removed, so nothing further will be placed for it.

## Related

- [What placing a bracket's protection writes first](what-placing-a-brackets-protection-writes-first.md)
- [Which child news a scheme acts on](which-child-news-a-scheme-acts-on.md)
- [Protection](protection.md)
