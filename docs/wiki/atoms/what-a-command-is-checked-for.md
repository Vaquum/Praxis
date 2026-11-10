---
row: N11-01
baseline: 49aa659
created: 2026-11-07 19:33 UTC
modified: 2026-11-08 02:10 UTC
evidence:
  - claim: "A command is refused unless its reference, its account, its venue and its symbol are each text with something left in them once trimmed"
    source: "`nexus/infrastructure/praxis_connector/trade_command.py` 101-103, or 109-111, or 113-115, or 117-119"
  - claim: "Its kind must be one of the three named ones, and the amount it names a finite figure at or above nought"
    source: "`nexus/infrastructure/praxis_connector/trade_command.py` 105-107, the three named at `nexus/infrastructure/praxis_connector/trade_command_type.py` 23-25, or `nexus/infrastructure/praxis_connector/trade_command.py` 121-127"
  - claim: "Its moment must be a moment"
    source: "`nexus/infrastructure/praxis_connector/trade_command.py` 129-131"
  - claim: "Thirteen further things it may leave out are each refused where present and wrong, every test for one standing behind a test for its absence"
    source: "`nexus/infrastructure/praxis_connector/trade_command.py` 137-139, or 141-147, or 149-155, or 157-159, or 161-165, or 167-171, or 173-177, or 179-181, or 183 into 184-186, or 193-199, or 201-205, or 207-213, or 215-219"
  - claim: "A deadline given as a true-or-false is refused by a test for that alone, the test beside it for a whole number counting such a thing as one"
    source: "`nexus/infrastructure/praxis_connector/trade_command.py` 194 against 195, raising at 199"
---
# What a command is checked for

A command is refused for failing any one of a fixed list of checks.

## What must be there

Its reference, [its account](what-an-account-is.md), [its venue](what-a-venue-is.md) and its symbol, each text with something left once the blank space is trimmed off. Its kind, which must be one of the three named ones. The amount it names, which must be a finite figure at or above nought. And its moment, which must be a moment.

## What need not be, and is checked anyway

Thirteen more things pass these checks when left out. Each is refused where it is there and wrong, and every one of those tests stands behind a test for the thing being absent, so leaving it out is never what these checks turn back. [What each kind must carry](what-each-kind-of-command-must-carry.md) is its own subject.

## The true-or-false deadline

[A deadline](deadlines.md) given as a true-or-false is refused by a test written for that alone. It needs one: the test beside it, which asks for a whole number, counts a true-or-false as one of those.

## Related

- [What each kind of command must carry](what-each-kind-of-command-must-carry.md)
- [The settings a command rewrites](the-settings-a-command-rewrites.md)
- [The marker a command's moment must carry](the-marker-a-commands-moment-must-carry.md)
