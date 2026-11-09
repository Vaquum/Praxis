---
row: P177-01
baseline: 49aa659
created: 2026-11-16 09:00 UTC
modified: 2026-11-16 09:00 UTC
evidence:
  - claim: "The part at the cursor is the one sent, and its size comes from the plan at that place"
    source: "`execution_manager.py` 5904, then 5905, then 5908"
  - claim: "A send that answers nothing freezes the work and the pass ends there"
    source: "`execution_manager.py` 5910, then 5911-5916, then 5917"
  - claim: "An order not already ended joins the live children"
    source: "`execution_manager.py` 5919, then 5920 into 5921"
  - claim: "The cursor moves on by one, whatever the part filled"
    source: "`execution_manager.py` 5923"
  - claim: "Where parts remain, the next run time is set a gap ahead and progress recorded"
    source: "`execution_manager.py` 5925, then 5926, then 5927"
  - claim: "Where none remain the next run time is forgotten, and progress recorded only where live children stand"
    source: "`execution_manager.py` 5928, then 5929, then 5930 into 5931"
  - claim: "The settling is then attempted, and does nothing while a live child remains"
    source: "`execution_manager.py` 5933, reaching 6355, then 6356"
---
# What moves a scheme on to its next part

Each turn of [work fed out over time](work-fed-out-over-time.md) sends the part at the cursor and then moves the cursor on, whatever that part did.

## The sending

The part at the cursor is the one sent, and its size comes from the plan at that place. A send that answers nothing freezes the work, and the pass ends there with the cursor where it was.

An order that came back and has not already ended joins the live children, which is the list the settling reads.

## The moving on

The cursor moves on by one. Nothing about the fill is consulted: a part that filled nothing advances the schedule exactly as a part that filled in full.

Where parts remain, the next run time is set a gap ahead and progress recorded. Where none remain, the next run time is forgotten — and progress is recorded only where live children stand, so a last part whose order has already ended writes no progress at all.

## The settling

Attempted at the end of every turn, and it does nothing while a live child remains.

## Related

- [Work fed out over time](work-fed-out-over-time.md)
- [What calling off a scheme's children leaves behind](what-calling-off-a-schemes-children-leaves-behind.md)
- [What is cleared before a scheme's ending is written](what-is-cleared-before-a-schemes-ending-is-written.md)
