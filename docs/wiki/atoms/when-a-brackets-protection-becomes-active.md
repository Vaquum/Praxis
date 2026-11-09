---
row: P150-02
baseline: 49aa659
created: 2026-11-15 19:30 UTC
modified: 2026-11-15 19:30 UTC
evidence:
  - claim: "The submission is written to the record and applied before the bracket is told anything about it"
    source: "`execution_manager.py` 5028, then 5029, ahead of 5031"
  - claim: "The bracket is then given the order's name, the average entry price and the three protective prices, and only after all five is its protection called active"
    source: "`execution_manager.py` 5031, then 5032, then 5033, then 5034, then 5035, then 5036"
  - claim: "The bracket is written back into the account's own brackets after that"
    source: "`execution_manager.py` 5037"
  - claim: "Each fill the venue's answer already carried is then written as a fill against the exit's name, on the protective side, each stamped as it is built"
    source: "`execution_manager.py` 5039, then 5040-5051, the exit named at 5047, the side at 5049"
  - claim: "The bracket was already marked as having its protection placed, long before any of this"
    source: "`execution_manager.py` 4906, ahead of 5028-5037"
---
# When a bracket's protection becomes active

A bracket's protection is called active only after five things have been written onto the bracket, and the order itself is recorded before any of them.

## The order first

The submission is written to the record and applied before the bracket is told anything about it. So the record holds the protective order while the bracket still says nothing about which order protects it.

## The five, then the word

The order's name, the average entry price, and the three protective prices. Only once all five stand is the protection called active, and only then is the bracket written back into the account's own brackets.

So "active" is the last thing set rather than the first, and nothing reading the bracket mid-way can see it active with its prices missing.

## What was already true

The bracket was marked as having its protection **placed** long before any of this — [before the pair was even built](what-placing-a-brackets-protection-writes-first.md). Placed and active are two marks, set far apart, and the gap between them covers the whole send.

## The fills that came with the answer

Each fill the venue's answer already carried is written as a fill against the exit's name, on the protective side. Each is stamped as it is built rather than at one shared moment.

## Related

- [What placing a bracket's protection writes first](what-placing-a-brackets-protection-writes-first.md)
- [The active-protection test written twice](the-active-protection-test-written-twice.md)
- [Protection](protection.md)
