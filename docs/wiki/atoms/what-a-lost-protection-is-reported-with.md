---
row: N14-06
baseline: 49aa659
created: 2026-11-08 06:15 UTC
modified: 2026-11-08 06:15 UTC
evidence:
  - claim: "Four of its fields are walked by name, and each is refused unless it is text with something left in it once trimmed"
    source: "`nexus/infrastructure/praxis_connector/protection_remediation.py` 41-42 over the four names, into 45-47"
  - claim: "Its moment must be a moment and must carry the UTC marker itself, both weighed by one test rather than two"
    source: "`nexus/infrastructure/praxis_connector/protection_remediation.py` 49-54"
  - claim: "The attempt number must be a whole number at or above one"
    source: "`nexus/infrastructure/praxis_connector/protection_remediation.py` 58 and 59, raising at 61-62"
  - claim: "A true-or-false is refused by a test of its own set ahead of the one for whole numbers, which would otherwise count such a thing as one"
    source: "`nexus/infrastructure/praxis_connector/protection_remediation.py` 57 before 58"
---
# What a lost protection is reported with

The record saying a bracket's protection was lost and dealt with is refused for failing any one of a fixed list of checks.

## The four fields walked by name

The account, the record's own reference, the entry command's reference, and the reason. One loop takes the four by name and holds each to the same rule: text with something left once the blank space is trimmed off.

## The moment

It must be a moment, and it must carry the universal-time marker itself. One test asks both, so a moment of the wrong kind and a moment of the right kind in the wrong zone are refused by the same line.

## The attempt number

A whole number at or above one.

A true-or-false is refused by a test set ahead of that. It needs to be: the test beside it, which asks for a whole number, counts a true-or-false as one of those, and true would pass the lower bound as well.

## Related

- [When protection is lost](when-protection-is-lost.md)
- [Protection](protection.md)
- [The marker a command's moment must carry](the-marker-a-commands-moment-must-carry.md)
