---
row: P74-01
baseline: 49aa659
created: 2026-11-08 21:46 UTC
modified: 2026-11-08 21:46 UTC
evidence:
  - claim: "Both of a report's moments must carry a zone that gives an offset, each weighed in a test of its own"
    source: "`venue_adapter.py` 504-506, then 507-512"
  - claim: "A report of a trade must then carry the fill that proves it, and a report of anything else has its fill fields cleared"
    source: "`venue_adapter.py` 514-515, or 519"
  - claim: "A trade must carry something in the field naming the venue's own trade, refused only where that field is absent, so an empty name passes"
    source: "`venue_adapter.py` 529-531, testing for absence alone"
  - claim: "It must name the asset a fee was taken in, and must carry a quantity and a price each finite and above nought"
    source: "`venue_adapter.py` 533-535, then 537-545"
  - claim: "Its fee must be finite and is held to nothing about its sign, so a fee of nought and a fee below nought both pass"
    source: "`venue_adapter.py` 547-549"
  - claim: "The asset a fee was taken in is refused for being empty by a test of truth rather than one of kind"
    source: "`venue_adapter.py` 533"
  - claim: "A report of a trade answers as soon as the fill is proved"
    source: "`venue_adapter.py` 517"
---
# What an execution report is held to

A report from a venue carries either an execution or a change of an order's standing, and which of the two decides what it must hold.

## Both moments

Each must carry a zone that gives an offset, weighed in a test of its own, so a reader of a complaint learns which moment was bare.

## A report of a trade

It must carry something in the field naming the venue's own trade. That field is refused only where it is absent, so a name that is empty passes, and nothing asks whether what is there came from a venue.

It must name the asset a fee was taken in, and must carry a quantity and a price, each finite and above nought.

Its fee must be finite, and is held to nothing about its sign. A fee of nought passes, and so does one below nought.

The asset is refused for being empty by a test of truth rather than one of kind, so an empty name and a name of some other kind that counts as nothing are refused alike.

## A report of anything else

Its fill fields are cleared, which [the clearing](what-a-non-trade-report-loses-quietly.md) does by writing over them.

A report of a trade answers as soon as its fill is proved, so the clearing cannot reach one.

## Related

- [What a non-trade report loses quietly](what-a-non-trade-report-loses-quietly.md)
- [What a fill is](what-a-fill-is.md)
