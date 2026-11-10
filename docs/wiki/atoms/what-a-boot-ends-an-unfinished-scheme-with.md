---
row: P142-02
baseline: 49aa659
created: 2026-11-09 11:05 UTC
modified: 2026-11-09 11:05 UTC
evidence:
  - claim: "The scheme's own projection is read first, and its absence is reported and the ending abandoned"
    source: "`execution_manager.py` 2701, then 2702 into 2709"
  - claim: "One moment is taken and used for every record the ending writes"
    source: "`execution_manager.py` 2711, used at 2723, and 2736, and 2760"
  - claim: "The figures are the admitted totals rather than the raw ones"
    source: "`execution_manager.py` 2712-2714"
  - claim: "The target is the scheme's whole amount, and the average price the admitted money over the admitted amount, or nothing where nothing was admitted"
    source: "`execution_manager.py` 2715, then 2717-2718"
  - claim: "A state change is written to the record and applied, naming the cursor reached, the amount admitted, no live children and no next run"
    source: "`execution_manager.py` 2721-2730, then 2731, then 2732"
  - claim: "An outcome is then written and applied, cancelled, naming the boot's own reason, and the command marked terminal"
    source: "`execution_manager.py` 2734-2744, then 2745, then 2746, then 2747"
  - claim: "The outcome handed on carries the slices done as the cursor held to the total, so a cursor past the total reads as the total"
    source: "`execution_manager.py` 2757, then 2758"
---
# What a boot ends an unfinished scheme with

A scheme a restart cannot resume is ended at boot rather than left, and the ending is written from the figures the accounting admitted rather than from what the projections hold.

## What it reads first

The scheme's own projection. Where there is none the ending is abandoned and reported — there is nothing to take a cursor or a target from.

One moment is then taken and used for every record the ending writes, so the state change, the outcome record and the outcome handed on all carry the same timestamp.

## The figures

[The admitted totals](two-ways-of-asking-what-a-command-filled.md) rather than the raw ones. The target is the scheme's whole amount. The average price is the admitted money over the admitted amount, and nothing at all where nothing was admitted.

So a scheme whose fills never passed through admission is ended as having filled nothing, and its ending says so.

## What is written

A state change, to the record and then applied: the cursor reached, the amount admitted, no live children, no next run, and the state cancelled.

Then an outcome, to the record and then applied: cancelled, naming the boot's own reason, carrying the admitted figures and the target. The command is marked terminal.

## The one figure that is trimmed

The outcome handed on carries the slices done as the cursor held to the total. A cursor standing past the total reads as the total, so nothing downstream sees more slices done than the scheme had.

## Related

- [Two ways of asking what a command filled](two-ways-of-asking-what-a-command-filled.md)
- [What stops a scheme being resumed](what-stops-a-scheme-being-resumed.md)
- [What a restart puts back](what-a-restart-puts-back.md)
