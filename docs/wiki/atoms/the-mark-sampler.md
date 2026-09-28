---
row: P3-09
baseline: 49aa659
created: 2026-09-28 11:26 UTC
modified: 2026-09-28 18:01 UTC
evidence:
  - claim: "A gap that is not above zero is refused"
    source: "`mark_sampler.py` 56-57"
  - claim: "It samples, then waits the gap, over and over"
    source: "`mark_sampler.py` 131-141"
  - claim: "Each attempt asks the price source for a price"
    source: "`mark_sampler.py` 113"
  - claim: "No price means no sample is added"
    source: "`mark_sampler.py` 115-116"
  - claim: "A price is written to the record as a sample"
    source: "`mark_sampler.py` 118-125"
---
# The mark sampler

The **mark sampler** writes down what the market was worth from time to time, so a paper run has something to measure against between its trades.

It samples, waits the gap it was given, and goes again — refusing a gap that is not above zero. So the spacing is a wait between attempts rather than a promise about when each lands.

## When there is no price

Each attempt asks the price source for a price. Where none comes back, that attempt adds no sample.

What the source does otherwise is its own business: it may hand back the same price twice running, and the sampler writes both down without knowing they are the same.

## Why the samples matter

[The report](the-paper-report.md) reads these samples alongside the fills.

The fills alone say what each closed trade made. The samples are what let the account be valued while a position is open and nothing is trading — which is what separates a run that sat through a drawdown from one that never had a position at all.

## Related

- [The paper report](the-paper-report.md)
- [The event spine](the-event-spine.md)
