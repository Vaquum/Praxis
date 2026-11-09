---
row: P20-02
baseline: 49aa659
created: 2026-11-08 15:33 UTC
modified: 2026-11-08 15:33 UTC
evidence:
  - claim: "A buy's ladder change is weighed on prices and shares that are the amended ones where amended and the original ones where not"
    source: "`validate_trade_modify.py` 66-72, reached only for a buy at 97-98 before 100-107"
  - claim: "A change must name prices or shares or both"
    source: "`praxis/core/domain/ladder_dca_modify.py` 43-45"
  - claim: "Shares that do not match the new prices in number raise what is committed"
    source: "`validate_trade_modify.py` 74-75"
  - claim: "Otherwise the two sides are each added up, every price against its share, and a new figure above the original raises it"
    source: "`validate_trade_modify.py` 77-79, worked out at 47-50"
  - claim: "A side with no shares at all gives each of its own rungs an equal share, so the two sides can be compared as averages across different numbers of rungs"
    source: "`validate_trade_modify.py` 43-45, called twice at 77-79"
---
# How a ladder's change is weighed

A change to [a buy's ladder](work-fed-out-over-time.md) is weighed as one figure against another: each rung's price against that rung's share, added up, new against original. A sell's never reaches this road.

## What the new figure is made of

A change must name prices or shares, and may name both. What is weighed is the amended prices where prices were amended and the original prices where they were not, and the same for the shares.

So a change naming shares alone is still weighed on the original prices, and the figure rises where the reshuffle moves weight onto a dearer rung.

## Where there are no shares

A ladder may carry none, and then each of its rungs takes an equal share of one — so that side's figure is its average rung price.

Each side is worked out that way on its own. A change naming three cheaper rungs where the original had two unweighted ones is therefore compared average against average, and is accepted where the new average is lower.

## The count that cannot be weighed

Where shares are in play and come to a different number than the new prices, the change raises what is committed and is turned back. There is no pairing to compare.

That catches a change of rung count on a ladder whose shares were set, the original shares staying and no longer lining up.

## Related

- [What counts as raising what a buy commits](what-counts-as-raising-what-a-buy-commits.md)
- [Changing work already sent](changing-work-already-sent.md)
- [Work fed out over time](work-fed-out-over-time.md)
