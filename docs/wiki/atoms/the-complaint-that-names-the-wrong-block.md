---
row: N60-04
baseline: 49aa659
created: 2026-11-12 18:30 UTC
modified: 2026-11-12 18:30 UTC
evidence:
  - claim: "The helper reading an optional figure words its complaint with the risk-controls block's name fixed in front of the field it was given"
    source: "`nexus/infrastructure/manifest.py` 305"
  - claim: "The three limits in that block pass their own plain field names to it, so for them the wording reads true"
    source: "`nexus/infrastructure/manifest.py` 360, and 361, and 362"
  - claim: "A strategy's price collar is read by the same helper, and passes a field name naming the strategy"
    source: "`nexus/infrastructure/manifest.py` 543-546"
  - claim: "So a collar that will not convert is complained about under the risk-controls block's name, with the strategy's name inside the field part"
    source: "`nexus/infrastructure/manifest.py` 545 reaching 305"
---
# The complaint that names the wrong block

The helper that reads an optional figure out of [a manifest](the-settings-a-host-is-given.md) builds its complaint with one block's name fixed in front of whatever field it was handed.

## Where the wording is right

[The three account limits](what-the-risk-controls-block-is-held-to.md) are read through it, and each passes its own plain field name. A limit that will not convert is therefore complained about under that block and that key, which is where it was written.

## Where it is not

A strategy's price collar is read through the same helper. What it passes as the field name names the strategy and the collar together.

So a collar written as something that will not convert is complained about under the risk-controls block's name, with the strategy's name sitting inside the field part — pointing a reader at a block the collar was never in.

## What that costs

The figure is still refused, and the complaint still carries the value as written and the strategy it came from, so the fault can be found. What the message gets wrong is where to look for it.

## Related

- [What the risk-controls block is held to](what-the-risk-controls-block-is-held-to.md)
- [What a money figure loses on the way in](what-a-money-figure-loses-on-the-way-in.md)
