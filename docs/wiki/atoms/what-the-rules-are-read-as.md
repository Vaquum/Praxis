---
row: P114-02
baseline: 49aa659
created: 2026-11-09 08:44 UTC
modified: 2026-11-09 08:44 UTC
evidence:
  - claim: "The rules are gathered by their own kind, and any entry that is not a mapping or names no kind is passed over"
    source: "`binance_adapter.py` 2206-2210"
  - claim: "Three kinds are demanded by name, and every one missing is named in the refusal together"
    source: "`binance_adapter.py` 2212, then 2213, then 2215 into 2216-2217"
  - claim: "Five figures are read from those three and each turned into an exact decimal"
    source: "`binance_adapter.py` 2222, and 2223, and 2224, and 2225, and 2226"
  - claim: "The two asset names are read with an empty one standing in where the answer gave none"
    source: "`binance_adapter.py` 2227, and 2228"
  - claim: "A missing field or a figure that will not convert becomes a venue failure naming the symbol"
    source: "`binance_adapter.py` 2219-2220 into 2230, then 2231-2232"
---
# What the rules are read as

The rules the venue returns are gathered by kind, three kinds are demanded, and five figures are read out of them.

## The gathering

By their own kind. Any entry that is not a mapping, or that names no kind, is passed over — so a malformed entry costs only itself rather than the whole answer.

## The three demanded

Demanded by name. Every one missing is named in the refusal together, so a caller learns all of what is absent rather than the first thing absent.

## The five figures

Read from those three and each turned into an exact decimal: the step a price moves in, the step an amount moves in, the smallest and largest amount, and the smallest worth.

So every figure the venue sends as text becomes an exact decimal here, and none of them passes through a floating form on the way.

## The two names

The asset given and the asset taken, read with an empty one standing in where the answer gave none. These are the only two things read with a fallback — every figure is demanded.

## What a malformed answer becomes

A missing field, or a figure that will not convert, becomes a venue failure naming the symbol. So the symbol is in the message even though the fault is in the answer, which is what lets a reader tell which asking failed.

## Related

- [What the trading rules asking insists on](what-the-trading-rules-asking-insists-on.md)
