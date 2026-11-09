---
row: P155-01
baseline: 49aa659
created: 2026-11-09 12:06 UTC
modified: 2026-11-09 13:36 UTC
evidence:
  - claim: "The command's amount is insisted upon, and the bracket taken out of the account's brackets before anything is weighed"
    source: "`execution_manager.py` 4586, then 4587, then 4588"
  - claim: "Two sets of figures are read: the order's own raw fills, and the admitted totals for the command"
    source: "`execution_manager.py` 4590, then 4591, then 4592-4594"
  - claim: "Whether the entry filled at all is decided on the raw figure"
    source: "`execution_manager.py` 4596"
  - claim: "An entry that filled nothing is reported and ends with its order's status turned into a trade status, a rejection standing in for a status the mapping does not hold"
    source: "`execution_manager.py` 4596 into 4604-4611, the fallback at 4608"
  - claim: "The average entry price is worked out from the raw figures"
    source: "`execution_manager.py` 4615"
  - claim: "Whether it counts as filled or part filled is decided on the admitted figure against the command's amount"
    source: "`execution_manager.py` 4617-4618"
  - claim: "The outcome carries the admitted figures, with its average price worked out from those"
    source: "`execution_manager.py` 4621-4632"
  - claim: "The protection is placed only after that outcome has been built"
    source: "`execution_manager.py` 4635-4637, past 4621, the outcome answered at 4644"
---
# Which figures settle a bracket's entry

Settling a bracket's entry reads two sets of figures — what the order itself recorded and what the accounting admitted — and uses each for a different decision.

## What the raw figures decide

Whether the entry filled at all. An entry whose own order recorded nothing is reported and ended, its order's status turned into a trade status, with a rejection standing in for any status the mapping does not hold.

And the average entry price, which the protection's legs will rest on. So the price the protection is built around comes from the order, not from the accounting.

## What the admitted figures decide

Whether the entry counts as filled or part filled, weighed against the command's whole amount. And the figures the outcome itself carries, including its own average price.

So one entry can be reported as part filled on the admitted figure while its protection is sized from a raw figure that is larger.

## The order of the two writes

The bracket is taken out of the account's brackets before anything is weighed, and the protection is placed only after the outcome has been built — [which puts the bracket back](what-placing-a-brackets-protection-writes-first.md).

So the outcome for the entry exists before the protection is attempted, and a failure placing the protection cannot unsay it.

## Related

- [What placing a bracket's protection writes first](what-placing-a-brackets-protection-writes-first.md)
- [Two ways of asking what a command filled](two-ways-of-asking-what-a-command-filled.md)
- [How a bracket's news is told apart](how-a-brackets-news-is-told-apart.md)
