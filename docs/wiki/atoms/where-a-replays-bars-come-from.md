---
row: P4-16
baseline: 49aa659
created: 2026-10-03 20:39 UTC
modified: 2026-10-11 20:01 UTC
evidence:
  - claim: "Bars for a run over real history are read from two frames, one of predictions and one of prices"
    source: "`load_replay_bars.py` 62-63, called at `replay_api.py` 211-218"
  - claim: "Those bars are put into a scenario and handed to the runner"
    source: "`replay_api.py` 220-229 into 128, 153 and 109"
  - claim: "Only prediction rows marked usable are kept"
    source: "`load_replay_bars.py` 71, the mark at 29"
  - claim: "The two are joined on the shared stamp, keeping only stamps in both, and sorted"
    source: "`load_replay_bars.py` 72"
  - claim: "A price frame carrying an opening-stamp column marks the series as the dollar kind"
    source: "`load_replay_bars.py` 65, the column at 30"
  - claim: "For that kind the stamp is the close; otherwise the interval handed in is added to find it"
    source: "`load_replay_bars.py` 74 and 82"
  - claim: "A bar whose close falls outside the window asked for is passed over, both edges counting as inside"
    source: "`load_replay_bars.py` 84-85"
  - claim: "A window edge with no zone at all refuses the load"
    source: "`load_replay_bars.py` 58-60"
  - claim: "Each surviving row becomes one bar, carrying its stamp, its close, its two prices, the prediction cut to a whole number and its probability"
    source: "`load_replay_bars.py` 89-102"
---
# Where a replay's bars come from

A [replay](replay.md) over real history takes its bars from two frames per series: one of predictions, one of prices. Both are read whole, and what survives three filters becomes [the scenario](what-a-replay-is-given.md) handed to the runner.

## What survives

Only prediction rows marked usable are kept.

Those are joined to the prices on the stamp they share. The join keeps only stamps present in both, so a prediction with no price, or a price with no prediction, drops out.

A bar whose closing moment falls outside the window asked for is passed over. Both edges of that window count as inside it.

## Which moment is the close

A price frame carrying an opening-stamp column marks the series as the dollar kind. For that kind a bar's stamp is already its closing moment.

Otherwise the interval handed in is added to the stamp to find it — the interval given, rather than one measured between the stamps actually there.

## What a bar carries

Each surviving row becomes one bar: its stamp, its closing moment, its opening and closing price, the prediction cut to a whole number, the probability behind it, and for the dollar kind the opening stamp as well.

Both edges of the window must carry a zone. One that does not refuses the load outright.

## Related

- [The frames a replay writes](the-frames-a-replay-writes.md)
- [What a replay is given](what-a-replay-is-given.md)
