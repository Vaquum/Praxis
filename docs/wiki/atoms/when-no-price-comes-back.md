---
row: P4-38
baseline: 49aa659
created: 2026-10-03 20:33 UTC
modified: 2026-10-03 20:37 UTC
evidence:
  - claim: "A file not there yields nothing"
    source: "`arrow_price_store.py` 93-95"
  - claim: "So does one that cannot be read"
    source: "`arrow_price_store.py` 97-101"
  - claim: "So does one empty, or missing either of the two columns it needs"
    source: "`arrow_price_store.py` 103-105"
  - claim: "So does one whose stamp column is anything but signed sixty-four-bit whole numbers"
    source: "`arrow_price_store.py` 107-112"
  - claim: "So does a frame the filtering or the sorting fails on"
    source: "`arrow_price_store.py` 118-122"
  - claim: "So does a frame with no closed bar in it"
    source: "`arrow_price_store.py` 124-125"
  - claim: "So does a last closed bar whose stamp is further behind now than the gap it was given, taken three times over by default"
    source: "`arrow_price_store.py` 128-129 and 131-140, the three defaulted at 30, held at 61"
  - claim: "So does a price that is neither a whole nor a fractional number, true and false included"
    source: "`arrow_price_store.py` 150-152"
  - claim: "So does an endless price, or one that is not a number, and one that will not convert"
    source: "`arrow_price_store.py` 154-162"
  - claim: "Nine of those ten write a warning before giving nothing back, each instead of the others"
    source: "`arrow_price_store.py` 94, 100, 104, 108-111, 121, 132-139, 151, 155 and 161"
  - claim: "The one that does not is the frame with no closed bar"
    source: "`arrow_price_store.py` 124-125"
---
# When no price comes back

[The reader of the bars](where-the-bars-are-kept.md) gives nothing back in ten cases. Each is a case of the file, the frame, or the price in it being unusable.

## The file

A file that is not there. One that cannot be read. One empty, or missing either of the two columns it needs.

One whose stamp column is anything but signed sixty-four-bit whole numbers. One the filtering or the sorting fails on.

## The frame

A frame with no closed bar in it yet. A last closed bar whose stamp is further behind now than the gap the reader was given, taken three times over by default. That is the guard against a feed that has frozen. It counts from the stamp, so for a series whose stamp is an opening, it allows two gaps past the close. And the gap is the one handed in rather than one measured between bars — for a series stamped at the close, that is how often predictions are made rather than how long a bar lasted.

## The price

A price that is neither a whole nor a fractional number — true and false among those refused, and a decimal too. One that is endless, or not a number at all. One that will not convert.

## Which are quiet

Nine of the ten are logged as a warning. Having no closed bar yet is the quiet one.

## Related

- [Where the bars are kept](where-the-bars-are-kept.md)
- [The mark sampler](the-mark-sampler.md)
