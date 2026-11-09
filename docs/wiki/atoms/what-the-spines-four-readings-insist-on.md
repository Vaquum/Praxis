---
row: P96-01
baseline: 49aa659
created: 2026-11-09 07:38 UTC
modified: 2026-11-09 07:38 UTC
evidence:
  - claim: "A reading of the new deduplication rows builds a set of triples as the rows arrive, each part cast to the kind the comparison needs"
    source: "`event_spine.py` 739 into 740-743"
  - claim: "A reading of the legacy rows builds its triples from the row's own first three values, cast to nothing"
    source: "`event_spine.py` 797 into 798"
  - claim: "A reading of one stored fact answers it as text, or answers nothing where no row came back"
    source: "`event_spine.py` 812-813, then 815"
  - claim: "The scan over the fill payloads builds its refusal before it reads a single row"
    source: "`event_spine.py` 758-762, ahead of 765"
  - claim: "A payload that will not parse, or that lacks any of the three fields it needs, refuses with that one message"
    source: "`event_spine.py` 767-771 into 772-773"
  - claim: "Any of the three arriving as something other than text refuses with the same message"
    source: "`event_spine.py` 775-779 into 780"
  - claim: "Each row's symbol and its triple are gathered, and the two sets answered together"
    source: "`event_spine.py` 782, and 783, then 785"
---
# What the spine's four readings insist on

Four readings pull facts out of the spine's file, and they differ in how much they insist the file is what it should be.

## The two that cast

A reading of the new deduplication rows builds a set of triples as the rows arrive, each part cast to the kind the comparison needs. A reading of the legacy rows builds its triples from the row's own first three values, cast to nothing.

So the two sets being compared are built under different rules, and they agree only while the legacy rows hold what the casting would have made of them anyway.

## The one that may answer nothing

A reading of one stored fact answers it as text, or answers nothing where no row came back. The absence is the answer rather than a failure, which is why [every caller weighs it](what-the-spine-asks-of-its-own-identity.md).

## The one that insists

The scan over the fill payloads builds its refusal before it reads a single row — one message, used for every way a row can be wrong.

A payload that will not parse refuses. One lacking any of the three fields it needs refuses. Any of the three arriving as something other than text refuses. All three refusals carry that same message, so the message says what was needed rather than what was wrong.

Each row's symbol and its triple are gathered, and the two sets answered together.

## Related

- [What the first migrations add and prove](what-the-first-migrations-add-and-prove.md)
