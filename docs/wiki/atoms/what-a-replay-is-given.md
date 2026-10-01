---
row: P3-04
baseline: 49aa659
created: 2026-09-30 19:29 UTC
modified: 2026-10-01 09:06 UTC
evidence:
  - claim: "A scenario carries the account, the series, a step length, the symbol and its venue rules, the starting money, the strategy text and the bars"
    source: "`replay_scenario.py` 63-70"
  - claim: "The run also takes a directory and a run number"
    source: "`run_replay.py` 103-112 and 121-122"
  - claim: "It makes the directory and three below it, and nothing removes them at the end"
    source: "`run_replay.py` 103-108 against the ending at 174-177 and `launcher.py` 3904-3941"
  - claim: "A bar carries a shared timestamp, its closing moment, its opening and closing price, a prediction and a probability"
    source: "`replay_scenario.py` 37-43"
  - claim: "A prediction that is not 0 or 1 is refused and the tick skipped"
    source: "Nexus `predict_loop.py` 399-405"
  - claim: "Where a bar carries its own opening timestamp, the store takes the shared timestamp as the closing moment rather than adding the step length"
    source: "`run_replay.py` 234-235 into `materialize_bar_frames.py` 76-77, with the effect at `arrow_price_store.py` 115"
  - claim: "The closing price is the price the venue fills at"
    source: "`run_replay.py` 246 into `replay_venue_adapter.py` 111 and 240-258"
  - claim: "The strategy text is written into the working directory"
    source: "`run_replay.py` 110"
  - claim: "That directory is put on the import path, and taken off when the run ends"
    source: "`launcher.py` 4071 into 2450-2451, undone from `run_replay.py` 177 at 189-192"
  - claim: "The account's settings are written out from the scenario"
    source: "`run_replay.py` 112 and 321-332"
  - claim: "The starting money is cut to a whole number there, and that cut figure is what sizing sees"
    source: "`run_replay.py` 319 and 321-324, read back at Nexus `manifest.py` 421-427 and `sequencer.py` 246, sized on at `launcher.py` 2516-2518"
  - claim: "The summary scores against the uncut figure"
    source: "`run_replay.py` 301 into `build_replay_report.py` 56 and 371"
---
# What a replay is given

A **scenario** is the whole of what a [replay](replay.md) is handed: an [account](what-an-account-is.md) name, a series name and the seconds one step in it stands for, a symbol and the venue's rules for it, starting money, a strategy, and the bars themselves.

Alongside it the run takes a directory to work in and a number for the run. It makes that directory and three below it at the start, and leaves all four behind at the end for whoever called it.

## The bars

Each bar carries a shared timestamp, the moment it closes, its opening and closing price, a prediction, which is refused unless it is 0 or 1, and the probability behind it. A bar may also carry its own opening timestamp; where it does, the store takes that shared timestamp as the closing moment rather than adding the step length.

The closing price is the price [the venue](the-replay-venue.md) fills at.

## The strategy is text

The strategy arrives as the text of a module. The run writes it into the working directory, which is put on the import path so it can be loaded and taken off again when the run ends.

The account's settings are written out from the scenario too. The starting money is cut to a whole number there, so sizing works from the whole number while [the summary](what-a-replay-reports.md) scores against the uncut figure.

## Related

- [Replay](replay.md)
- [What a replay reports](what-a-replay-reports.md)
