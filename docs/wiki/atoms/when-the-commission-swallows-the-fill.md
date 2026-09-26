---
row: P2-33
baseline: 49aa659
created: 2026-09-26 06:31 UTC
modified: 2026-09-26 17:41 UTC
evidence:
  - claim: "A fill may be made with its fee equal to or above its amount"
    source: "`events.py` 593-595, which only refuses a fee below zero"
  - claim: "A commission equal to the amount delivers nothing"
    source: "`trading_state.py` 459"
  - claim: "Delivering nothing leaves a record holding something as it was"
    source: "`trading_state.py` 501-505 for one side, 506-507 for the other"
  - claim: "Against a record holding nothing, the same-side sum divides zero by zero"
    source: "`trading_state.py` 502-503"
  - claim: "With nothing held, delivering nothing builds a record of nothing that stands"
    source: "`trading_state.py` 487-497, zero allowed by `position.py` 52-53"
  - claim: "With nothing held, delivering less than nothing is refused as the record is built"
    source: "`position.py` 52-53, reached at `trading_state.py` 489-497"
  - claim: "Against a record on the same side the average is worked out and set before the amount"
    source: "`trading_state.py` 502-504 ahead of 505"
  - claim: "A total of zero is divided by"
    source: "`trading_state.py` 503"
  - claim: "An average below zero is refused as it is set"
    source: "`position.py` 67-69"
  - claim: "An amount below zero is refused as it is set"
    source: "`position.py` 63-65"
  - claim: "Against a record on the other side the holding grows"
    source: "`trading_state.py` 506-507"
---
# When the commission swallows the fill

A [fill](what-a-fill-is.md) is refused for a commission below zero and for nothing else about its size, so one may be made whose commission equals or exceeds the amount it reports. A buy charged in BTC then [delivers](the-commission-and-the-amount.md) nothing, or less than nothing.

## A commission equal to the amount

Such a fill delivers nothing. A record already holding something is left exactly as it was, whichever side it is on.

Where nothing is held yet, a record holding nothing is built, and it stands.

That empty record is where it turns. A second such fill on the same side divides a total of nothing by a total of nothing, and the sum fails.

## A commission larger than the amount

Such a fill delivers less than nothing, and where nothing is held yet, building the record is refused outright.

Against a record on the same side, three things are done in order, and each can stop the one after it. The remaining total is divided by, so a fill landing it exactly on zero fails there. The average is worked out from that division and set, so an average below zero is refused next. Only then is the amount set, and an amount below zero is refused there.

Where none of the three bites, the holding simply shrinks — a buy taking away from what it was meant to add to.

Against a record on the other side the subtraction runs the other way, and the holding grows.

## Related

- [The commission and the amount](the-commission-and-the-amount.md)
- [Holdings](holdings.md)
