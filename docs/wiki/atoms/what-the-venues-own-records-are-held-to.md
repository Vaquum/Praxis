---
row: P74-03
baseline: 49aa659
created: 2026-11-08 21:46 UTC
modified: 2026-11-08 21:46 UTC
evidence:
  - claim: "A trade the venue describes must carry a moment with a zone that gives an offset, and is asked nothing else"
    source: "`venue_adapter.py` 248-250, the whole of that record's checking"
  - claim: "A record of money moving must carry such a moment, an amount finite and above nought, and a direction among the named ones"
    source: "`venue_adapter.py` 322-324, then 326-328, then 330-333"
  - claim: "That direction is matched against a set of words rather than asked its kind, and the complaint lists the words allowed in sorted order"
    source: "`venue_adapter.py` 330, the complaint built at 331"
  - claim: "A quantization must carry exactly one of a snapped quantity and a reason for refusal, the two weighed against each other by their presence"
    source: "`venue_adapter.py` 399-406"
  - claim: "The fill-scoped part of a trade is taken from the trade's own fields without any of them being weighed again"
    source: "`venue_adapter.py` 99-106"
  - claim: "Six fields are copied across and none is read from anywhere else, so the narrowing restates no figure of its own"
    source: "`venue_adapter.py` 99-106, each field read off the trade"
---
# What the venue's own records are held to

The records a venue's answers arrive in are weighed as they are built, and three of them are weighed differently.

## A trade

One thing: a moment carrying a zone that gives an offset. Its quantity, its price and its fee all go unweighed here, and are left to whatever reads them.

## Money moving in or out

Three things: such a moment, an amount finite and above nought, and a direction among the named ones.

The direction is matched against a set of words rather than asked its kind, so a bare word of the right spelling passes. The complaint lists the words allowed, in sorted order.

## A quantization

Exactly one of a snapped quantity and a reason for refusal. The two are weighed against each other by their presence, so carrying both and carrying neither are refused on the same line.

## The fill inside a trade

The fill-scoped part of a trade is taken from the trade's own fields, and none of them is weighed again.

Six fields are copied across, and none is read from anywhere else. So the narrowing restates no figure of its own: a fill shaped this way carries exactly what the trade it came from carried.

## Related

- [What an execution report is held to](what-an-execution-report-is-held-to.md)
- [What a fill is](what-a-fill-is.md)
