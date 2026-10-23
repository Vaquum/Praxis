---
row: N3-12
baseline: 49aa659
created: 2026-10-22 23:40 UTC
modified: 2026-10-23 09:00 UTC
evidence:
  - claim: "The fee figure taken off a sale's gain comes in on the report rather than being worked out where it is used"
    source: "`nexus/infrastructure/praxis_connector/outcome_processor.py` 533"
  - claim: "Praxis sets it as a rate times what the part filled came to, on both the whole-fill and the part-fill road"
    source: "`praxis/outcome_translator.py` 282 and 312"
  - claim: "The rate the running host uses is a thousandth, set once where the translator is built"
    source: "`praxis/launcher.py` 193 into 2800"
  - claim: "Praxis does read what the venue charged, taking the commission and the asset it was charged in off each fill it is told about"
    source: "`praxis/infrastructure/binance_adapter.py` 942-943"
  - claim: "Its own ledger books that charge rather than the rate, on a buy and on a sale alike"
    source: "`praxis/core/account_ledger.py` 298-310 and 354-356, the assets it will take at 336-338"
  - claim: "The same figure is what the fee held back is settled against"
    source: "`nexus/infrastructure/praxis_connector/outcome_processor.py` 225-230 into `nexus/core/capital_controller/capital_controller.py` 924 and 955-957"
---
# What a fee figure is worked out from

A fee figure is what a trade is treated as having cost to make, and the one Nexus is given is worked out from a rate.

## Where it comes from

The figure arrives on the report of a fill. Praxis sets it as a rate times what that part of the fill came to — the same way on the road for a whole fill and the road for a part of one. That report is where the rate stops: the venue is asked nothing in working it out.

The rate the running host uses is a thousandth, fixed where the translator is built.

## What it reaches

Two things. It is taken off the gain to give [what a sale came to](which-fills-come-back-with-a-result.md), so every realized result is a thousandth of the sale lighter than the price difference alone. And it is the figure [the fee held back](what-the-fee-reserve-absorbs.md) is settled against when the fill is reported.

Praxis does read what the venue charged — the commission and the asset it came in — and its own ledger books that figure. What carries the rate instead is the report Nexus is given, so a venue charging something else leaves the two sides' accounts of the same trade apart by the difference.

## Related

- [Which fills come back with a result](which-fills-come-back-with-a-result.md)
- [What the fee reserve absorbs](what-the-fee-reserve-absorbs.md)

---

Created 2026-10-22 23:40 UTC · Last modified 2026-10-23 09:00 UTC
