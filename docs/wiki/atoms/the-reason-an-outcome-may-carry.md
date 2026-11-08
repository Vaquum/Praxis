---
row: N12-03
baseline: 49aa659
created: 2026-11-08 06:30 UTC
modified: 2026-11-08 08:20 UTC
evidence:
  - claim: "A refusal must carry a reason with something left in it once trimmed"
    source: "`nexus/infrastructure/praxis_connector/trade_outcome.py` 119 into 120-122"
  - claim: "Every other kind is refused for carrying a refusal's reason at all"
    source: "`nexus/infrastructure/praxis_connector/trade_outcome.py` 123-125, reached rather than 120-122"
  - claim: "A cancellation may carry a reason or leave it out, and one it carries must have something left in it once trimmed"
    source: "`nexus/infrastructure/praxis_connector/trade_outcome.py` 127 into 128-133"
  - claim: "Every other kind is refused for carrying a cancellation's reason at all"
    source: "`nexus/infrastructure/praxis_connector/trade_outcome.py` 134-136, reached rather than 128-133"
---
# The reason an outcome may carry

A reason in words belongs to two of an outcome's kinds — a refusal, and [a cancellation](how-a-trade-is-cancelled.md) — and each of the two is held to its own rule.

## A refusal

A refusal must carry a reason, and that reason must have something left in it once the blank space is trimmed off. A refusal leaving the field out is turned back, and so is one putting nothing but spaces in it.

## A cancellation

A cancellation may carry a reason or leave it out. One it carries must have something left in it once trimmed, so the field is either absent or says something.

## Every other kind

The two reasons are checked separately, and each is refused on every kind but its own. A cancellation carrying a refusal's reason is turned back, and so is a refusal carrying a cancellation's.

## Related

- [What an outcome is checked for](what-an-outcome-is-checked-for.md)
- [What a fill must carry](what-a-fill-must-carry.md)
- [The two measures an outcome reports](the-two-measures-an-outcome-reports.md)
- [How a trade is cancelled](how-a-trade-is-cancelled.md)
