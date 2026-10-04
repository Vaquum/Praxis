---
row: P3-24
baseline: 49aa659
created: 2026-09-30 19:38 UTC
modified: 2026-10-04 11:43 UTC
evidence:
  - claim: "What comes back is the bar and fill counts, the amounts bought and sold, the fees, the outcome endings, the closed round-trips and the summary figures"
    source: "`run_replay.py` 303-312"
  - claim: "The bar count is the length of the scenario's own list"
    source: "`run_replay.py` 304"
  - claim: "The fill counts, the amounts, the fees and the outcome endings are worked out from the record, read back in one go at the end"
    source: "`run_replay.py` 168-170 and 286-301"
  - claim: "The round-trips and the summary take those same fills together with the scenario's bars and starting money"
    source: "`build_replay_report.py` 53-57 and 77-82, pairing at 232-303"
  - claim: "The bar closes stand in for marks, so a position still open is still valued"
    source: "`build_replay_report.py` 53 into 323-335"
  - claim: "The profit is read from the run's risk figures, not the record"
    source: "`run_replay.py` 309"
  - claim: "An entry adds nothing to those; only a fill reducing a position does"
    source: "Nexus `outcome_processor.py` 448-451, gated at 260 and added at 812"
  - claim: "The summary charges a round-trip both fees, the entry's and the exit's"
    source: "`build_replay_report.py` 269-273, apportioned at 224-229"
  - claim: "The risk figure subtracts only the exit fee, off a price that carries no fee"
    source: "Nexus `outcome_processor.py` 523-533, against the fee-bearing figure it does not use at 479-485"
---
# What a replay reports

A **result** is the single thing a [replay](replay.md) hands back when its walk is done: how many bars were walked and how many [fills](what-a-fill-is.md) there were, how much was bought and how much sold, what the fees came to, how the [outcomes](what-an-outcome-is.md) ended, the closed round-trips, and [the summary figures](the-metrics.md).

## Where each part comes from

How many bars were walked is the length of the scenario's own list. The fill counts, the amounts bought and sold, the fees and the outcome endings are worked out from [the record](the-event-spine.md), read back in one go once the walk is done.

The round-trips and the summary take those same recorded fills and put them together with [the scenario's](what-a-replay-is-given.md) own bars and starting money. The bar closes stand in for marks, so a position still open is still valued.

The profit stands apart: it is read from the run's risk figures rather than the record, and an entry adds nothing to those — only a fill reducing a position does.

## Two profits that need not agree

The summary charges a round-trip both fees, the entry's and the exit's.

The risk figure subtracts the exit fee only, and takes the entry side from a price that carries no fee at all. The fee-bearing price is kept alongside and left unused. So the two account for what an entry cost differently, and on the same closed trade they need not agree.

## Related

- [What a replay is given](what-a-replay-is-given.md)
- [The metrics](the-metrics.md)
