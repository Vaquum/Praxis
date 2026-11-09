---
row: P156-01
baseline: 49aa659
created: 2026-11-09 12:10 UTC
modified: 2026-11-09 12:10 UTC
evidence:
  - claim: "The command's amount and the shape of the change are both insisted upon"
    source: "`execution_manager.py` 10078-10079, then 10080, then 10081"
  - claim: "A scheme held for protection or draining is reported and the change dropped"
    source: "`execution_manager.py` 10083 into 10091"
  - claim: "A scheme already owing a terminal answer is reported and dropped too"
    source: "`execution_manager.py` 10093 into 10099"
  - claim: "A volume-weighted change carrying weights is reported and dropped"
    source: "`execution_manager.py` 10101 into 10107"
  - claim: "The new slice count and interval are worked out from the change against the ones standing"
    source: "`execution_manager.py` 10109, then 10110, then 10111-10113"
  - claim: "What is left to fill is the command's amount less the raw projected fills, and what is left to do is the new count less the cursor"
    source: "`execution_manager.py` 10115, then 10116, then 10117"
  - claim: "Nothing left to fill, or no slices left to run, each report and drop the change"
    source: "`execution_manager.py` 10119 into 10123, or 10125 into 10133"
  - claim: "A changed slice count replans the remaining amount over the remaining slices against the venue's lot step, and a replan that refuses leaves the schedule as it was"
    source: "`execution_manager.py` 10135, then 10136, then 10137, then 10138-10139, then 10140 into 10147"
  - claim: "The replanned amounts replace only the part of the plan the cursor has not reached"
    source: "`execution_manager.py` 10149"
---
# What a scheme's change replans

Changing a fed-out order's schedule replans only the part it has not reached, and a replan it cannot work out leaves the schedule exactly as it was.

## The three refusals

A scheme held for protection or draining. Neither can be resumed by a change, and the two are reported apart because they mean different things.

A scheme already owing a terminal answer. And a volume-weighted change that carries weights, which this road will not take.

## The two figures

What is left to fill: the command's amount less the raw projected fills. What is left to do: the new slice count less the cursor.

Nothing left to fill, or no slices left to run, each report and drop the change. So a scheme that has filled its whole amount cannot be given a new schedule even if its slices are unfinished.

## The replan

Only where the slice count actually changed. The remaining amount is spread over the remaining slices against the venue's lot step — nothing standing in for the step where no rules are held.

A replan that refuses leaves the schedule as it was, and says so. So a change that cannot be divided is a no-op rather than a failure.

## What the replan replaces

Only the part of the plan the cursor has not reached. The slices already run keep the amounts they ran with, so the record of what was done stays true.

## Related

- [How a schedule change is carried out](how-a-schedule-change-is-carried-out.md)
- [What a resumed scheme comes back holding](what-a-resumed-scheme-comes-back-holding.md)
- [A change waiting out a hold](a-change-waiting-out-a-hold.md)
