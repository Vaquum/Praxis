---
row: P12-01
baseline: 49aa659
created: 2026-11-08 14:05 UTC
modified: 2026-11-08 14:05 UTC
evidence:
  - claim: "The bars are numbered into runs by a running count of the entry marks"
    source: "`praxis/metrics/limen_snapshot.py` 194"
  - claim: "One trade is the held bars sharing a number"
    source: "`praxis/metrics/limen_snapshot.py` 198-199"
  - claim: "Where no bar is marked as an entry, no trade is counted at all"
    source: "`praxis/metrics/limen_snapshot.py` 191-192"
  - claim: "A trade's return is its bars' returns multiplied together rather than added"
    source: "`praxis/metrics/limen_snapshot.py` 200-201"
---
# What counts as one trade

Every per-trade figure in a replay's report rests on one definition, and it is drawn from the bars rather than from any record of an order.

## How the bars are grouped

A running count of the entry marks numbers the bars. Each mark raises the count, so every bar carries the number of the entry it followed.

One trade is the bars of that number which held a position. A bar numbered with a trade but holding nothing is left out.

## Where there is nothing to number

Where no bar is marked as an entry, no trade is counted. The report then carries no per-trade figures rather than carrying zeroes.

## How a trade's return is reached

Its bars' returns are multiplied together, not added. Two bars each returning a tenth give just over a fifth — a shade over twenty-one parts in a hundred rather than twenty.

So a long trade's figure compounds, and a reader adding its bars would come out low.

## Related

- [How the bars are cut into days](how-the-bars-are-cut-into-days.md)
- [What a replay reports](what-a-replay-reports.md)
