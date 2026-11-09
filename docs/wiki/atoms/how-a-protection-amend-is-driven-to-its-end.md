---
row: P143-01
baseline: 49aa659
created: 2026-11-09 11:09 UTC
modified: 2026-11-09 14:05 UTC
evidence:
  - claim: "The amend's own figures are taken off the bracket, and four of them are insisted upon"
    source: "`execution_manager.py` 9519-9525, then 9526, and 9527, and 9528, and 9529, the closing command named at 9532 and the old pair read at 9534"
  - claim: "What the entry delivered is read as the filled amount net of its base-asset fees"
    source: "`execution_manager.py` 9531, into 2648"
  - claim: "The venue is asked what the cancelled pair actually filled"
    source: "`execution_manager.py` 9536, then 9539-9541, then 9543-9546"
  - claim: "A venue failure there records the protection's state as unknown, marks the bracket so, stamps the moment and abandons the amend"
    source: "`execution_manager.py` 9547, then 9548 into 9549-9552, then 9553, then 9554, then 9555, then 9564"
  - claim: "Otherwise the protective fills are reconciled against what the venue said"
    source: "`execution_manager.py` 9566-9570"
  - claim: "Fills that will not reconcile park the amend as cancel-confirmed for the scan to retry, the first such pass stamping when the waiting began"
    source: "`execution_manager.py` 9571, then 9572 into 9573, then 9575, then 9576 into 9577, then 9585"
  - claim: "Past the restore deadline the replacement is placed from what the venue said anyway, rather than parked again"
    source: "`execution_manager.py` 9596, against 9577-9585, past the test at 9576"
  - claim: "The old pair is recorded cancelled where its order still stands locally, under the venue's own name for it or the one the cancel returned"
    source: "`execution_manager.py` 9598 into 9599-9602, then 9604-9611"
---
# How a protection amend is driven to its end

An amend whose cancel the venue confirmed is finished by this one routine, and what it does first is ask the venue what the cancelled pair actually filled.

## What it reads before asking

The amend's figures off the bracket — the two list names, the three prices and the version — four of which it insists upon rather than tolerating.

What the entry delivered, read as [the filled amount net of its base-asset fees](two-ways-of-asking-what-a-command-filled.md). What the old pair is projected to have filled, and what the exit command is projected to have filled.

## The two ways it stops short

A venue failure answering that question records the protection's state as unknown, marks the bracket so, stamps the moment, and abandons the amend. The watchdog for that state takes it from there.

Fills that will not reconcile park the amend as cancel-confirmed instead, for the scan to retry — and the first such pass stamps when the waiting began.

Those two parkings are deliberately different states. One says the venue could not be asked; the other says it answered and the books have not caught up.

## What the deadline changes

Past the restore deadline the replacement is placed from what the venue said anyway, rather than parked again. A gap in the books that the balance reconciler will surface is preferred to leaving the position unprotected.

## The record of the old pair

Where the old pair's order still stands locally it is recorded cancelled, under the venue's own name for it — the one the cancel returned, or the one the local order carries.

## Related

- [What a protection of unknown fate is rebuilt as](what-a-protection-of-unknown-fate-is-rebuilt-as.md)
- [How protection's prices are changed](how-protections-prices-are-changed.md)
- [Two ways of asking what a command filled](two-ways-of-asking-what-a-command-filled.md)
