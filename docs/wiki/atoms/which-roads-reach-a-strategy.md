---
row: N10-02
baseline: 49aa659
created: 2026-11-07 04:30 UTC
modified: 2026-11-07 05:05 UTC
evidence:
  - claim: "Outside the tests each of the eight ways in is reached from exactly one line, and every one of those lines is on the Nexus side"
    source: "`nexus/startup/sequencer.py` 728, 555 and 592, `nexus/strategy/predict_loop.py` 337, `nexus/core/outcome_loop.py` 420, `nexus/strategy/timer_loop.py` 117, and `nexus/startup/shutdown_sequencer.py` 326 and 818, with no mention of any of the eight anywhere under `praxis/`"
---
# Which roads reach a strategy

Eight roads reach a strategy, and outside the tests each one is reached from a single line.

## Where the lines are

Three are in the one place that runs a start: beginning the strategy, [handing back the state it saved](what-a-start-does-with-a-strategys-saved-state.md), and replaying an event to it. Two are in the one place that runs a stop: [asking it to finish](what-a-strategy-is-handed-when-it-is-asked-to-stop.md) and [asking it for its state to keep](what-a-stopping-host-saves-of-its-strategies.md). The other three are each a loop of its own — [a prediction](what-the-prediction-loops-stop-leaves-running.md), [an outcome](which-fills-come-back-with-a-result.md), and [a timer](what-a-turn-of-a-timer-does.md).

## One side only

Every one of those eight lines is on the Nexus side, and Praxis's own modules name none of the eight.

## Related

- [The wrapper every strategy sits behind](the-wrapper-every-strategy-sits-behind.md)
- [What a strategy must provide](what-a-strategy-must-provide.md)
- [What a turn of a timer does](what-a-turn-of-a-timer-does.md)
