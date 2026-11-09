---
row: N78-01
baseline: 49aa659
created: 2026-11-09 02:48 UTC
modified: 2026-11-09 02:48 UTC
evidence:
  - claim: "Each of the three names a dust close is given must be text with something other than spaces in it"
    source: "`nexus/infrastructure/praxis_connector/outcome_processor.py` 662 into 663-664, then 666 into 667-668, then 670 into 671-672"
  - claim: "The three are weighed in turn, the trade's name first, the reason second and the close's own name last"
    source: "`nexus/infrastructure/praxis_connector/outcome_processor.py` 662, then 666, then 670"
  - claim: "All three are weighed before any lock is taken"
    source: "`nexus/infrastructure/praxis_connector/outcome_processor.py` 670-672, ahead of 674"
  - claim: "The positions lock is taken first and the duplicate-name lock inside it"
    source: "`nexus/infrastructure/praxis_connector/outcome_processor.py` 674, then 675"
  - claim: "A close that got through answers that it happened, from outside both locks"
    source: "`nexus/infrastructure/praxis_connector/outcome_processor.py` 716, the locks let go after 702"
---
# What a dust close refuses before it touches anything

[Closing a position as dust](where-a-positions-last-scraps-go.md) is given three names, and each must be text with something other than spaces in it.

## The three

The trade's name first, the reason second, and the close's own name last. Each is refused the same way: it must be text, and that text must hold a character other than a space.

So a name of a single space is refused exactly as an empty one is, and a close asked for with a reason left blank never reaches the position.

## Before the locks

All three are weighed before any lock is taken. A badly asked close therefore holds nothing up: it raises while the positions are still free for every other caller.

## The order of the locks

The positions lock first, and the lock guarding the record of names already used inside it. Nothing in this path takes them the other way about.

## The answer

A close that got through answers that it happened, and answers from outside both locks — the locks are let go once the position is gone from the book, before the answer is given.

## Related

- [Closing a position as dust](where-a-positions-last-scraps-go.md)
- [What a pending sale does to the dust](what-a-pending-sale-does-to-the-dust.md)
