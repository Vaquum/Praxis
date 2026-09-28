---
row: P3-01
baseline: 49aa659
created: 2026-09-28 08:58 UTC
modified: 2026-09-28 17:09 UTC
evidence:
  - claim: "A replay builds its own clock and venue"
    source: "`run_replay.py` 114-115"
  - claim: "It works in directories it makes itself"
    source: "`run_replay.py` 103-110"
  - claim: "It walks the bars of the scenario in turn"
    source: "`run_replay.py` 230"
  - claim: "Each bar lays out the figures the strategy will read"
    source: "`run_replay.py` 231-241"
  - claim: "It tells the venue the price to fill at, then moves the clock to the bar's close"
    source: "`run_replay.py` 246-247"
  - claim: "The strategy is then run once for that bar"
    source: "`run_replay.py` 249-250"
  - claim: "The queued work is waited on, under a real time limit"
    source: "`run_replay.py` 264-266, waiting on the queue at `execution_manager.py` 3600-3604"
  - claim: "A command counts as done once its handling returns"
    source: "`execution_manager.py` 4021-4022, past the handling at 3993-4019"
  - claim: "The outcomes ready are then taken until none is left"
    source: "`run_replay.py` 269"
  - claim: "Work fed out in slices can outlive that wait, its later slices still due"
    source: "`execution_manager.py` 4021-4022 against 5925-5927"
  - claim: "The record is read back once the walk is done"
    source: "`run_replay.py` 168-170"
  - claim: "The report is built from that and from the scenario's own figures"
    source: "`build_replay_report.py` 53-57 and 77-83"
---
# Replay

A **replay** runs the ordinary trading path over bars that have already happened, on a clock moved by hand. Nothing reaches a real venue.

It is the same path. The checks, the [worker](how-waiting-work-is-drained.md), the [record](the-event-spine.md) and the [outcomes](what-an-outcome-is.md) are the ones the live host uses; what is swapped underneath them is [the venue](the-replay-venue.md), [the clock](the-replay-clock.md) and the file written to.

## One bar at a time

The run walks the scenario's bars in order. For each it lays out the figures the strategy will read, tells the venue what price to fill at, and moves the clock to that bar's close.

Only then is the strategy run, once, for that bar.

## Settling before moving on

The run then waits for the queued work to be taken up, under a real time limit, and takes whatever [outcomes](how-an-outcome-is-delivered.md) are ready until none is left.

That waits for the handling of each queued command to return. For an ordinary market order the handling covers the fill and the outcome, so the bar really is done with it.

Work [fed out in slices](work-fed-out-over-time.md) is the exception. Its first handling returns with later slices merely scheduled, so it outlives the wait and carries into following bars.

## Reading the result

Outcomes are delivered as the run goes, in the ordinary way. What waits until the end is the summary: the record is read back once the walk is done, and the report is built from it together with the scenario's own figures.

## Related

- [The replay clock](the-replay-clock.md)
- [The replay venue](the-replay-venue.md)
