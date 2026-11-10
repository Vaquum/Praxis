---
row: P137-01
baseline: 49aa659
created: 2026-11-09 10:44 UTC
modified: 2026-11-09 10:44 UTC
evidence:
  - claim: "One pass gathers the bracket starts, the latest active protection, the amends under their versions, which commands have an amend unresolved and which were put right already"
    source: "`execution_manager.py` 1604-1608, then 1609, then 1610 into 1611"
  - claim: "An amend requested or a protection whose state is unknown marks the command unresolved"
    source: "`execution_manager.py` 1613 into 1614-1617, or 1619 into 1620"
  - claim: "A protection reported active clears both marks and is kept as the latest"
    source: "`execution_manager.py` 1622 into 1623-1625"
  - claim: "A protection reported failed clears the unresolved mark and sets the put-right one"
    source: "`execution_manager.py` 1627 into 1628-1629"
  - claim: "A start whose command carries either mark is passed over"
    source: "`execution_manager.py` 1631, then 1632 into 1633"
  - claim: "A command that will not rebuild from its start is reported and passed over"
    source: "`execution_manager.py` 1635-1636, then 1637 into 1645"
  - claim: "The entry's name is worked out from the mode, the command and the entry's place, and a name the account holds no order for passes the bracket over"
    source: "`execution_manager.py` 1647-1648, the place at 180, then 1650, then 1651 into 1652"
  - claim: "A resting protection whose entry filled nothing is passed over, leaving it to reconciliation"
    source: "`execution_manager.py` 1693 into 1697"
  - claim: "A command with an active protection recorded whose protection is no longer resting is passed over rather than falling to the awaiting-protection road"
    source: "`execution_manager.py` 1733 into 1738"
  - claim: "A protection order that exists and is doing anything but submitting passes the bracket over too"
    source: "`execution_manager.py` 1740 into 1741"
---
# What stops a bracket being resumed

A bracket start found in the history is resumed only if it survives six tests, and the first two of them are answered by a pass over the history that runs before any bracket is looked at.

## What the gathering pass remembers

The bracket starts. The latest protection reported active. The amends, kept under their versions. Which commands have an amend unresolved, and which were put right already.

An amend requested, or a protection whose state is unknown, marks a command unresolved. A protection reported active clears both marks. A protection reported failed clears the unresolved mark and sets the put-right one.

So a protection that failed and was then restored resumes as active, because the later record cleared what the earlier one set.

## The six that pass a bracket over

A command carrying either mark. A command that will not rebuild from its start, which is reported. An entry name the account holds no order for — the name worked out from the mode, the command and the entry's place.

A resting protection whose entry filled nothing, which is left to reconciliation rather than resumed with legs that cannot be worked out.

A command with an active protection recorded whose protection is no longer resting, passed over rather than falling through to the road that would place protection afresh.

And a protection order that exists and is doing anything but submitting.

## Related

- [What a resumed bracket's protection is taken from](what-a-resumed-brackets-protection-is-taken-from.md)
- [What a restart puts back of a bracket](what-a-restart-puts-back-of-a-bracket.md)
- [Protection](protection.md)
