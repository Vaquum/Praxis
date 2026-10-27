---
row: N7-06
baseline: 49aa659
created: 2026-10-27 09:50 UTC
modified: 2026-10-27 12:10 UTC
evidence:
  - claim: "The stop clears a flag, raises an event and empties the record of what was due next, all under one lock"
    source: "`nexus/strategy/predict_loop.py` 256-259"
  - claim: "The loop reads a prediction already written, makes a signal of it, and hands that signal to the strategy"
    source: "`nexus/strategy/predict_loop.py` 390-399 into 413-423, handed over at 337-342"
  - claim: "The scheduler's turn begins by waiting on that event for a quarter of a second, and the raised event ends the loop there"
    source: "`nexus/strategy/predict_loop.py` 293, the span standing at 60"
  - claim: "A turn that got past that wait before the event was raised reads the flag under the lock and answers at once where it is down"
    source: "`nexus/strategy/predict_loop.py` 297-299"
  - claim: "Finding it up, it copies under the lock every pairing of a strategy and a series whose moment has come"
    source: "`nexus/strategy/predict_loop.py` 301-304"
  - claim: "Each copy is then taken outside the lock, with no reading of the flag between the copying and the first of them"
    source: "`nexus/strategy/predict_loop.py` 301-304 into 306-308, outside the lock taken at 297"
  - claim: "A take answers early wherever it cannot settle on a figure to hand over — among the reasons a reading no newer than the last one — before the strategy is asked at all"
    source: "`nexus/strategy/predict_loop.py` 327-329 before 337-342, the staleness among the reasons at 396-397"
  - claim: "Where the strategy answers with something that answer is submitted, and an empty answer is submitted nowhere"
    source: "`nexus/strategy/predict_loop.py` 346-347"
  - claim: "A take that raises is logged and the rest are still taken"
    source: "`nexus/strategy/predict_loop.py` 309-316"
  - claim: "The flag is read after each take, and that reading's next moment is set again only where the flag is still up"
    source: "`nexus/strategy/predict_loop.py` 317-322"
---
# What the prediction loop's stop leaves running

Stopping the loop that reads predictions and hands them to the strategies clears a flag, raises an event and empties the record of what was due next. A reading already copied for the turn in hand is still taken.

## The turn

A turn begins by waiting on that event for a quarter of a second, and the raised event ends the loop right there. A turn that got past that wait first reads the flag under the lock, answers at once where it is down, and otherwise copies — under that lock — every reading whose moment has come: one pairing of a strategy with a series it watches.

It then takes each copy outside the lock, with no reading of the flag between the copying and the first take. So a stop landing after the copying leaves the remaining copies to be taken — the flag is read again after each one, but only to decide what to schedule next.

## What a take amounts to

A take reads a prediction already written, makes a signal of it, and hands that signal to the strategy. It answers early wherever it cannot settle on a figure to hand over — a reading no newer than the last one among the reasons — and does so before the strategy is asked at all.

Where the strategy answers with something, that answer is [submitted](how-a-decision-becomes-a-command.md); an empty answer goes nowhere.

A take that raises is logged and the rest are still taken.

## What the stop does reach

The flag is read after each take, and that reading's next moment is set again only where the flag is still up. So the batch finishes and nothing beyond it is scheduled.

## Related

- [What a loop's stop leaves running](what-a-loops-stop-leaves-running.md)
- [What the halted mode turns away](what-the-halted-mode-turns-away.md)

---

Created 2026-10-27 12:10 UTC · Last modified 2026-10-27 12:10 UTC
