---
row: P103-01
baseline: 49aa659
created: 2026-11-14 05:00 UTC
modified: 2026-11-14 05:00 UTC
evidence:
  - claim: "The balances expected are taken from the manager, and the venue asked for exactly those assets"
    source: "`praxis/trading.py` 1232, then 1234-1237"
  - claim: "A venue that refuses the asking ends the pass with a warning"
    source: "`praxis/trading.py` 1238 into 1243"
  - claim: "The pass ends too where events are still pending, or where the expected balances moved while the venue was being asked"
    source: "`praxis/trading.py` 1245-1247 into 1249"
  - claim: "Each asset's venue total is its free amount and its locked amount added together"
    source: "`praxis/trading.py` 1253"
  - claim: "Only a shortfall past that asset's own tolerance counts, a surplus or a small shortfall clearing what was remembered"
    source: "`praxis/trading.py` 1256-1257, then 1260 into 1261-1262"
  - claim: "A shortfall identical to the one last remembered for that asset is passed over"
    source: "`praxis/trading.py` 1264 into 1265"
  - claim: "So is one identical to a mismatch still waiting to be delivered"
    source: "`praxis/trading.py` 1267 into 1268-1269"
---
# What a balance comparison weighs

The comparison asks the venue what it holds, and reports only a shortfall it has not reported already.

## What is compared

The balances expected are taken from the manager, and the venue asked for exactly those assets. Each asset's venue total is its free amount and its locked amount added together, so money held against an order counts as held.

## The three ways the pass ends early

A venue that refuses the asking ends it with a warning. Events still pending end it. So does the expected balances having moved while the venue was being asked.

The last of those is the careful one: the answer in hand describes a moment that has passed, and comparing it against balances that have since changed would report a difference that is only the delay.

## What counts as a mismatch

Only a shortfall past that asset's own tolerance. A surplus does not, nor a shortfall inside tolerance — and either clears what was remembered for that asset.

So the venue holding more than expected is never reported, and only a shortage is.

## What is not reported twice

A shortfall identical to the one last remembered for that asset. And one identical to a mismatch still waiting to be delivered.

So the same unchanging shortfall is reported once, and a shortfall that worsens is reported again because the figure differs.

## Related

- [What becomes of a mismatch nobody took](what-becomes-of-a-mismatch-nobody-took.md)
