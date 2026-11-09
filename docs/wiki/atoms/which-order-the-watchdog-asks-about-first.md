---
row: P157-01
baseline: 49aa659
created: 2026-11-15 23:00 UTC
modified: 2026-11-15 23:00 UTC
evidence:
  - claim: "An account the manager does not hold ends the pass"
    source: "`execution_manager.py` 7357, then 7358 into 7359"
  - claim: "The brackets are walked over a copy, and any whose protection is not in doubt is passed over"
    source: "`execution_manager.py` 7361, then 7362 into 7363"
  - claim: "The replacement still owing is asked about before the protection the bracket holds, and a name appearing twice is asked about once"
    source: "`execution_manager.py` 7366-7373"
  - claim: "Each candidate is asked after in turn, and the first found working ends the asking"
    source: "`execution_manager.py` 7377, then 7379, then 7384 into 7385-7386"
  - claim: "A venue failure on a candidate is remembered and the next candidate tried all the same"
    source: "`execution_manager.py` 7380 into 7381-7382"
  - claim: "A candidate found working has the protection written back as active, and the bracket passed over"
    source: "`execution_manager.py` 7388 into 7389-7391, then 7392"
  - claim: "Where none was found working and any asking failed, the bracket is remediated as unconfirmable"
    source: "`execution_manager.py` 7394 into 7395-7396"
  - claim: "Where none was found working and every asking answered, the bracket is resolved as confirmed finished"
    source: "`execution_manager.py` 7398, past 7394"
---
# Which order the watchdog asks about first

A protection in doubt has two candidate lists, and the watchdog asks about the replacement still owing before the one the bracket holds.

## Why that order

An amend that got as far as placing its replacement leaves the newer list as the one most likely to be working. Asking about it first means the usual case is settled on the first question.

A name appearing in both places is asked about once, so a bracket whose replacement and protection are the same list costs one question rather than two.

## The three endings

A candidate found working has [the protection written back as active](how-a-protection-in-doubt-is-re-confirmed.md), and the asking stops at the first one found.

Where none was found working and any asking failed, the bracket is remediated as unconfirmable: the venue stayed silent on at least one candidate, which leaves the question open.

Where none was found working and every asking answered, the bracket is resolved as [confirmed finished](what-the-venue-is-asked-when-no-protection-is-working.md) — the venue was asked about everything and said no list is live.

## The failure that does not stop the asking

A venue failure on one candidate is remembered and the next candidate tried all the same. So a bracket whose first question failed can still be re-confirmed by its second, and only a bracket with no working candidate at all has that remembered failure consulted.

## Related

- [How a protection in doubt is re-confirmed](how-a-protection-in-doubt-is-re-confirmed.md)
- [What the venue is asked when no protection is working](what-the-venue-is-asked-when-no-protection-is-working.md)
- [What a protection of unknown fate is rebuilt as](what-a-protection-of-unknown-fate-is-rebuilt-as.md)
