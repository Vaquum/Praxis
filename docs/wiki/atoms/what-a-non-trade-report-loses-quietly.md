---
row: P74-02
baseline: 49aa659
created: 2026-11-13 05:30 UTC
modified: 2026-11-13 05:30 UTC
evidence:
  - claim: "Six fill fields are listed with the value each should hold on a report that is not a trade"
    source: "`venue_adapter.py` 279-286"
  - claim: "Five of the six are listed again as the ones whose presence is worth reporting"
    source: "`venue_adapter.py` 291-297"
  - claim: "The gathering of what to report walks the six and keeps only those among the five, so a stray value in the sixth is gathered nowhere"
    source: "`venue_adapter.py` 554-558"
  - claim: "A gathering holding anything writes a warning naming the kind of report, the order and the fields, in sorted order"
    source: "`venue_adapter.py` 560-567, sorted at 554"
  - claim: "The clearing then walks all six and writes the listed value over anything differing from it"
    source: "`venue_adapter.py` 569-571"
  - claim: "So the sixth field is cleared without being named, and a report arriving with it set is changed with no word said"
    source: "`venue_adapter.py` 569-571 covering 279-286, against the gathering at 557"
  - claim: "The writing goes round the sealing the record otherwise has"
    source: "`venue_adapter.py` 571"
---
# What a non-trade report loses quietly

A report carrying no execution has its fill fields cleared, and one of them is cleared without being mentioned.

## The two lists

Six fill fields are listed with the value each should hold on a report that is not a trade.

Five of those six are listed again, as the ones whose presence on such a report is worth reporting.

## What is reported

The gathering walks the six and keeps only those among the five. A gathering holding anything writes a warning naming the kind of report, the order it was about, and the fields, in sorted order.

## What is cleared

The clearing walks all six, and writes the listed value over anything differing from it.

So the field left out of the second list is cleared without being named. A report arriving with it set is changed, and nothing says so.

That field is the flag saying whether the order waited or took what was there — a modality rather than evidence of an execution, which is the reason given for leaving it out.

## How the writing is done

By the means that goes round the sealing the record otherwise has, so a record that cannot be changed changes itself at the moment of its making.

## Related

- [What an execution report is held to](what-an-execution-report-is-held-to.md)
- [What a fill is](what-a-fill-is.md)
