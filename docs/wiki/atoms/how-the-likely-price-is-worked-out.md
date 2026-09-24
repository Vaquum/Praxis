---
row: P1-06
baseline: 49aa659
created: 2026-09-20 17:33 UTC
modified: 2026-09-24 08:02 UTC
evidence:
  - claim: "The book is fetched before the walk"
    source: "`execution_manager.py` 4192-4205"
  - claim: "One side is walked: the sell offers for a buy, the buy bids for a sell"
    source: "`estimate_slippage.py` 111, by money 171"
  - claim: "The walk takes what is on offer level by level"
    source: "`estimate_slippage.py` 115-122, by money 175-181"
  - claim: "The average is the walked value over the units traded"
    source: "`estimate_slippage.py` 67, a money order passing value and units at 192"
  - claim: "The middle is halfway between the first price listed on each side"
    source: "`estimate_slippage.py` 55-56 with 61"
  - claim: "The order of the levels is never sorted or checked"
    source: "`estimate_slippage.py` 111-122"
  - claim: "The figure is average minus middle, over middle, times ten thousand"
    source: "`estimate_slippage.py` 68 with 23"
  - claim: "Nothing on a side, a top buy price of zero or less, or a top sell price below it, gives no middle"
    source: "either `estimate_slippage.py` 52-53 or 58-59"
  - claim: "A book too thin to fill the order gives no figure"
    source: "`estimate_slippage.py` 124-133, by money 182-190"
  - claim: "A failed request for the book also leaves no figure"
    source: "`execution_manager.py` 4222-4228"
---
# Estimating the likely price

Praxis estimates what [an order](what-a-trade-is.md) would average if it went to the venue right now, by walking the order book. The figure it produces feeds [the likely-price check](how-the-likely-price-is-checked.md).

## The walk

One side of the book is walked, the sell offers for a buy and the buy bids for a sell, one price level at a time, taking what is on offer at each until the order is filled. The total value of that, each level's price times the amount taken there, divided by the units traded, gives the average.

An order expressed as a sum of money to spend is walked the same way, spending down until the money runs out.

Only one side is ever walked. So long as the venue returns each side in price order, which is taken on trust and never checked, a buy's average lands at or above the middle and a sell's at or below it.

## The middle

Halfway between the first price listed on each side, which is taken to be the best one there.

## The figure

The average minus the middle, divided by the middle, multiplied by ten thousand: how far off the middle the average sits, counted in hundredths of one percent.

## When there is none

The book may have nothing on a side, or a top buy price of zero or less, or a top sell price below the top buy price. It may be too thin to fill the whole order. Or asking the venue for it may fail outright. Each of these leaves no figure at all.
