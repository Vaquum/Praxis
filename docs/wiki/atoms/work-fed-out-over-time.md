---
row: P2-19
baseline: 49aa659
created: 2026-09-27 14:09 UTC
modified: 2026-09-27 21:33 UTC
evidence:
  - claim: "Three ways of working send an amount out in parts spaced over time"
    source: "`execution_manager.py` 170-172, spaced at 5926-5929"
  - claim: "Fewer than two parts is refused as the settings are made"
    source: "`interval_slice_params.py` 36-43 with the figure at 16, and `scheduled_vwap_params.py` 50-52 with the figure at 20"
  - claim: "One record holds the total, the parts, which is next, how much has filled, the orders working and the next due time"
    source: "built at `trading_state.py` 251-259, kept up to date at 275-280"
  - claim: "Dividing evenly makes every part but the last the same size"
    source: "either `plan_even_slices.py` 56-58 or, where a step is known, 60-78"
  - claim: "A curve of weights sizes each part from its own weight"
    source: "either `plan_weighted_slices.py` 59-62 or, where a step is known, 65-76"
  - claim: "Either way the last part takes what is left"
    source: "`plan_even_slices.py` 70 and `plan_weighted_slices.py` 76"
  - claim: "Rounding down to a step happens only where the step is known"
    source: "`plan_even_slices.py` 56-58 doing none, the alternative at 60-78 doing it, the step read at `execution_manager.py` 5733-5734"
  - claim: "The first part goes at once, without waiting on a due time"
    source: "`execution_manager.py` 5800"
  - claim: "Later parts are looked at only on circuits that reach that work"
    source: "`execution_manager.py` 3969-3973, skipped while starting, paused or failed at 3902-3905"
  - claim: "A later part goes only where nothing is winding the work up and its time has come"
    source: "`execution_manager.py` 5831-5838"
  - claim: "After a part the next time is set from the gap, or cleared where none remain"
    source: "either `execution_manager.py` 5926-5929 or 5930-5931"
  - claim: "No order still working means it does not finish yet"
    source: "`execution_manager.py` 6352-6356"
  - claim: "With none working, it finishes once every part has been sent"
    source: "`execution_manager.py` 6372-6376"
  - claim: "A deadline reached first starts the winding up, which waits on the orders out"
    source: "`execution_manager.py` 5817-5824 into 8375-8383, waiting at 6355-6356"
  - claim: "Orders spread across price levels keep the same record and are sent one after another"
    source: "`execution_manager.py` 6136-6153, stopping on a failure at 6139-6146"
---
# Work fed out over time

Some work is not sent as one order. An amount is broken into parts, called **slices**, and the slices go out one at a time with a gap between them. Three ways of working do this. Asking for fewer than two parts is refused as the settings are made.

Praxis keeps one record for it all: the total, how many slices, which comes next, how much has filled, the orders still working, and when the next slice is due.

## How the slices are sized

Dividing evenly makes every slice but the last the same size. A curve of weights instead sizes each slice from its own weight, so early ones can be larger than late ones.

Either way the last slice takes what is left, so ten split three ways can be three, three and four. Each is rounded down to the step the venue trades in, but only where Praxis knows that step.

## When each one goes

The first slice goes at once. Each later one waits until its time has come, and [the worker](how-waiting-work-is-drained.md) looks only on circuits reaching this work — not while the account is starting, paused or failed.

Even then a slice goes only where nothing is winding the work up. Once one is sent, the next due time is set from the gap; where no slices remain, there is no next time.

## How it ends

The work finishes once no order it sent is still working and every slice has gone out.

[A deadline](deadlines.md) reached first starts [winding it up](work-already-under-way.md) instead, and that too waits on the orders already out.

Orders spread across price levels keep this same record, but are sent one after another rather than spaced, and a failure stops the rest.

## Related

- [The worker](how-waiting-work-is-drained.md)
- [Work already under way](work-already-under-way.md)
