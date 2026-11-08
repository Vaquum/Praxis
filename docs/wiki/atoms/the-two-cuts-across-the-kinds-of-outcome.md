---
row: N18-03
baseline: 49aa659
created: 2026-11-09 23:00 UTC
modified: 2026-11-09 23:00 UTC
evidence:
  - claim: "Six kinds of outcome are named"
    source: "`nexus/infrastructure/praxis_connector/trade_outcome_type.py` 26-31"
  - claim: "Four of the six are answered as endings"
    source: "`nexus/infrastructure/praxis_connector/trade_outcome_type.py` 37-42"
  - claim: "Two of the six are answered as fills"
    source: "`nexus/infrastructure/praxis_connector/trade_outcome_type.py` 48"
  - claim: "One kind is in both groups and one is in neither"
    source: "`nexus/infrastructure/praxis_connector/trade_outcome_type.py` 37-42 against 48, the six at 26-31"
---
# The two cuts across the kinds of outcome

Six kinds of outcome are named, and two questions cut across them without lining up.

## The six

An acknowledgement, a part fill, a full fill, a refusal, an expiry, and [a cancellation](how-a-trade-is-cancelled.md).

## The two cuts

Four of the six are answered as endings: the full fill, the refusal, the expiry and the cancellation. Two are answered as fills: the part fill and the full fill.

## Where they overlap and where they miss

The full fill is in both groups: it is a fill and it is an ending. The acknowledgement is in neither: nothing has filled and nothing has finished.

The other four sit in one group each. So a reader asking only whether an outcome is an ending learns nothing about whether anything filled, and a reader asking only whether it is a fill learns nothing about whether more is coming.

Both questions are needed to place a kind, and [the record carrying one](what-a-fill-must-carry.md) turns on the second of the two.

## Related

- [What a fill must carry](what-a-fill-must-carry.md)
- [What an outcome is checked for](what-an-outcome-is-checked-for.md)
- [How a trade is cancelled](how-a-trade-is-cancelled.md)
