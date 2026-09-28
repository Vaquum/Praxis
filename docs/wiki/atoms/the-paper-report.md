---
row: P3-08
baseline: 49aa659
created: 2026-09-28 11:22 UTC
modified: 2026-09-28 18:01 UTC
evidence:
  - claim: "It is built from fills and mark samples, every other kind passed over"
    source: "`paper_report.py` 41 and 42-46"
  - claim: "It can be built at any time, from what the record holds so far"
    source: "`launcher.py` 3360-3373"
  - claim: "The samples are put in time order first"
    source: "`paper_report.py` 42-46"
  - claim: "Trades and figures are worked out from the two together"
    source: "`paper_report.py` 57"
  - claim: "Both come back side by side"
    source: "`paper_report.py` 59-62"
  - claim: "The figures cover open positions too, from fills, marks and the starting money"
    source: "`build_replay_report.py` 129-142"
---
# The paper report

A **paper report** is how a paper-trading run is judged. It is not kept as the run goes: it is rebuilt from [the record](the-event-spine.md) out of the rows already written, and can be asked for at any point rather than only at the end.

Two kinds of row go into it and no others — the [fills](what-a-fill-is.md), and the mark samples [taken as the run went](the-mark-sampler.md). Everything else in the record is passed over.

## Why two kinds

The fills say what was traded and at what price. They are enough to work out what each closed trade made or lost.

They are not enough to say what the account was worth along the way. Between one trade and the next nothing is filled, yet an open position's worth moves with the market — so account values are built from the fills, the marks and the starting money together, and those cover positions still open.

## How it is put together

The samples are put in time order first, since the record keeps rows in the order they were written rather than the order things happened.

What comes back is two things side by side: the list of closed trades, and the run's summary figures.

## Related

- [The mark sampler](the-mark-sampler.md)
- [The event spine](the-event-spine.md)
