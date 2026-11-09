---
row: P176-01
baseline: 49aa659
created: 2026-11-16 08:30 UTC
modified: 2026-11-16 08:30 UTC
evidence:
  - claim: "The list is asked after by the name it was sent under"
    source: "`execution_manager.py` 5581, then 5582-5585, reached from 5513, then 5514"
  - claim: "A list the venue does not know answers nothing"
    source: "`execution_manager.py` 5586, then 5594"
  - claim: "An asking that fails answers nothing too"
    source: "`execution_manager.py` 5595, then 5604"
  - claim: "A list the venue reports as refused answers nothing as well"
    source: "`execution_manager.py` 5606, then 5614"
  - claim: "A list reported as having all its legs done has its standing worked out from those legs"
    source: "`execution_manager.py` 5616, then 5617-5619"
  - claim: "Anything else stands as open"
    source: "`execution_manager.py` 5620, then 5621"
  - claim: "The answer carries the venue's own list name, the standing, the legs' names and no placement fills"
    source: "`execution_manager.py` 5634-5641, the fills left empty at 5637"
  - claim: "Nothing answered has the entry remediated as unprotected"
    source: "`execution_manager.py` 4983, then 4990-4995, then 4997"
---
# What rescuing a protective pair by its list name answers

A protective pair whose send failed is looked for at the venue by the name it was sent under, and the answer is either the pair as the venue holds it or nothing at all.

## The three nothings

A list the venue does not know. An asking that fails. A list the venue reports as refused.

All three answer the same nothing, so the caller cannot tell a pair the venue turned away from a pair it could not ask about. Nothing answered has the entry remediated as unprotected either way.

## The somethings

A list reported as having all its legs done has its standing worked out from those legs — one may have filled, and which one matters.

Anything else stands as open: a list still working is a pair that is protecting.

## What the answer carries

The venue's own list name, the standing just settled, and the legs' names. No placement fills: whatever the pair filled arrives separately, by the legs' names rather than the list's.

## Related

- [What a failed protection replacement is looked for](what-a-failed-protection-replacement-is-looked-for.md)
- [When a protective pair counts as still protecting](when-a-protective-pair-counts-as-still-protecting.md)
- [When protection is lost](when-protection-is-lost.md)
