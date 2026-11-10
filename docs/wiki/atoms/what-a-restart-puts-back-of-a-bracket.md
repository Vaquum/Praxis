---
row: P4-57
baseline: 49aa659
created: 2026-10-14 11:05 UTC
modified: 2026-10-14 13:10 UTC
evidence:
  - claim: "A pair the record shows resting at the venue comes back active rather than being put up again"
    source: "`execution_manager.py` 1667-1674, the pair's mark read at 1622"
  - claim: "A pair missing, or still going out when the stop came, comes back waiting to be placed"
    source: "`execution_manager.py` 1740-1741"
  - claim: "Placement waits for the opening order to have ended with something filled"
    source: "`execution_manager.py` 4743, 4748 and 4753"
  - claim: "An amended pair no longer resting locally is passed over rather than falling back to the first pair"
    source: "`execution_manager.py` 1733-1738"
  - claim: "Passing it over rebuilds no bracket, and the watch walks only rebuilt brackets, so nothing picks it up"
    source: "`execution_manager.py` 1733-1738 against 7361-7362"
  - claim: "One whose change never settled comes back unknown, for the watch to ask about"
    source: "`execution_manager.py` 1831-1835, from the unsettled change at 1822"
  - claim: "A bracket with no entry fill at all is read from the entry order's filled amount"
    source: "`execution_manager.py` 1814"
---
# What a restart puts back of a bracket

What [a restart](what-a-restart-puts-back.md) makes of [a bracket](protection.md) turns on what its protective pair was doing when the stop came. Four states come back four different ways, and only one of them leads to a pair being sent.

## Resting

A pair the record shows resting at the venue comes back active. It is not put up a second time: it is already doing its job.

## Waiting to go up

A pair the record has nothing for, or has as still going out, comes back waiting to be placed. Still going out does not settle whether the venue has it: the answer may simply never have been recorded, which is why the name is worked out the same way every time and a pair already there is found rather than duplicated.

Placement itself waits for the opening order to have ended with something filled. A part-filled order still working already shows in the holdings, so the wait is for a settled amount to protect rather than for any exposure to exist.

## Mid-change

A pair whose change never settled comes back unknown. Nothing is sent for it: [the watch](when-protection-is-lost.md) asks the venue what became of it, and either finds it resting or treats the position as unprotected.

## Changed, and gone

A pair that was amended and is no longer resting locally is passed over entirely, rather than counted among those never up: the first pair's prices are stale by then, and putting them back would guard the position at the wrong levels.

Passing it over leaves no bracket rebuilt for it, and the watch only looks at brackets that were rebuilt — so nothing picks this one up. The position is unguarded and unwatched until something else reaches it.

## Related

- [What a restart puts back](what-a-restart-puts-back.md)
- [Protection](protection.md)
- [When protection is lost](when-protection-is-lost.md)

---

Created 2026-10-14 11:05 UTC · Last modified 2026-10-14 13:10 UTC
