---
row: P144-02
baseline: 49aa659
created: 2026-11-15 16:30 UTC
modified: 2026-11-15 16:30 UTC
evidence:
  - claim: "What a bracket still has unprotected is the entry's delivered amount, less the exit's projected fills with the candidates' own projections taken back out, less what the venue said those candidates filled"
    source: "`execution_manager.py` 7463"
  - claim: "The same shape is written again where an amend decides whether to place a replacement"
    source: "`execution_manager.py` 9614"
  - claim: "Both read the entry's delivered amount, which is the filled amount net of its base-asset fees"
    source: "`execution_manager.py` 7413, and 9531, both into 2648"
  - claim: "Both read the exit command's projected fills from the same helper"
    source: "`execution_manager.py` 7414, and 9533"
  - claim: "In the one the figures taken back out and added in are gathered over both candidate lists"
    source: "`execution_manager.py` 7429, then 7460, then 7461"
  - claim: "In the other they are the old list's alone"
    source: "`execution_manager.py` 9535, then 9544-9546"
  - claim: "A remainder at or below nothing drops the bracket in both"
    source: "`execution_manager.py` 7464 into 7480, and 9616 into 9617"
  - claim: "A remainder standing is remediated as naked in the one and protected afresh in the other"
    source: "`execution_manager.py` 7488-7495, against 9642-9649"
---
# The remainder subtraction written twice

How much of a bracket's position stands unprotected is worked out by one subtraction, and that subtraction is written in two places.

## The shape

The entry's delivered amount — the filled amount net of its base-asset fees — less the exit command's projected fills with the candidates' own projections taken back out, less what the venue said those candidates filled.

Taking the local projection back out before adding the venue's figure is what stops the same fill being counted twice, once as projected and once as reported.

## What differs between the two

In the one, the figures taken back out and added in are gathered over both candidate lists — the protection held and any replacement owing. In the other they are the old list's alone, because an amend knows exactly which list it cancelled.

Everything else is the same: the same two helpers give the entry's delivered amount and the exit's projection in both.

## What each does with the answer

A remainder at or below nothing drops the bracket in both places.

A remainder standing is remediated as unprotected in the one, and protected afresh in the other. So the same arithmetic leads to a flatten on one road and to a new protective pair on the other, and which road a bracket is on decides which.

## Related

- [What the venue is asked when no protection is working](what-the-venue-is-asked-when-no-protection-is-working.md)
- [When an amend places no replacement](when-an-amend-places-no-replacement.md)
- [What a lost protection is reported with](what-a-lost-protection-is-reported-with.md)
