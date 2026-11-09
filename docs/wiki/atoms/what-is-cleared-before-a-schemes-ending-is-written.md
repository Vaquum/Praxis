---
row: P170-02
baseline: 49aa659
created: 2026-11-16 05:30 UTC
modified: 2026-11-16 12:30 UTC
evidence:
  - claim: "The next run time is forgotten, the live children cleared, and the scheme taken off the account's live schemes"
    source: "`execution_manager.py` 6498, then 6499, then 6500, then 6501"
  - claim: "All three happen before the ending is recorded"
    source: "`execution_manager.py` 6501, then 6503"
  - claim: "The figures are then gathered from the admitted totals and the terminal report made"
    source: "`execution_manager.py` 6505-6507, then 6509-6518"
  - claim: "The report names the scheme's own place in its plan"
    source: "`execution_manager.py` 6515, and 6516"
  - claim: "The schemes the account holds are what a pass over due schemes walks"
    source: "`execution_manager.py` 6501, against 5816"
---
# What is cleared before a scheme's ending is written

Ending [work fed out over time](work-fed-out-over-time.md) clears three things about it before a word of the ending is recorded.

## The three

The next run time is forgotten. The live children are cleared. The scheme is taken off the account's live schemes.

The last of those is what matters most: the schemes the account holds are what a pass over due schemes walks, so a scheme taken off that list cannot have another part fired for it, whatever happens next.

## Then the writing

The ending is recorded, the figures gathered from the admitted totals, and the terminal report made, naming the scheme's own place in its plan.

Because the clearing comes first, a failure in any of that writing leaves a scheme that fires nothing and reports nothing — gone from the live set, with its ending unwritten. The clearing is not undone.

## Related

- [Work fed out over time](work-fed-out-over-time.md)
- [What ending a scheme forgets](what-ending-a-scheme-forgets.md)
- [What a partial report of a scheme leaves standing](what-a-partial-report-of-a-scheme-leaves-standing.md)
