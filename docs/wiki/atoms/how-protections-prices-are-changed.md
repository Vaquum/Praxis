---
row: P4-48
baseline: 49aa659
created: 2026-10-14 07:25 UTC
modified: 2026-11-09 14:05 UTC
evidence:
  - claim: "No live bracket, no resting pair, a pair not active, no entry price and prices that will not resolve are each logged and returned rather than raised"
    source: "`execution_manager.py` 9388-9393, 9395-9400, 9402-9409 and 9411-9426"
  - claim: "The change is written down before the venue is touched"
    source: "`execution_manager.py` 9463 and 9464"
  - claim: "A cancel the venue refuses, and a query of what it filled that fails, both leave the pair unknown"
    source: "`execution_manager.py` 9457, then 9458, then 9459-9472 and 9567-9583"
  - claim: "Fills that will not reconcile park the change until a deadline, and the replacement is then sized from the venue's own figure"
    source: "`execution_manager.py` 9590-9604 against 9606-9608"
  - claim: "Nothing left to protect ends it with no replacement"
    source: "`execution_manager.py` 9616-9624"
  - claim: "A remainder under the venue's smallest size or value ends it with no replacement too"
    source: "`execution_manager.py` 9630-9640"
  - claim: "A replacement whose send fails and whose query cannot be answered, the venue not having it included, leaves the pair unknown"
    source: "`execution_manager.py` 9689-9706"
  - claim: "One the venue returns marked rejected is taken as protection lost"
    source: "`execution_manager.py` 9976-9979, then 9980-9981, then 9983, read at 9708-9712"
  - claim: "One already ended when it comes back is left unknown rather than marked resting"
    source: "`execution_manager.py` 9749-9767"
---
# How protection's prices are changed

Changing the prices of [a protective pair](protection.md) takes the resting pair down and puts a fresh one up for what of the position is still open. Each step is written down before the venue is called, and a restart rebuilds an unsettled change as unknown rather than at the stage it had reached.

## Refused before it starts

A change is logged and returned rather than raised where there is no live bracket, no resting pair, no entry price to measure from, or prices that will not resolve — and where the pair's standing is anything but active: unknown, failed, or mid-change already.

## Down, then counted

The cancel goes out, and what the old pair filled on its way off is asked for. A cancel the venue refuses leaves the pair unknown, as does a query that fails, and [the watch](when-protection-is-lost.md) takes over.

Fills that cannot be reconciled park the change instead, retried on each scan, and past a deadline it goes ahead anyway — sizing the replacement from the venue's figure rather than the record's.

## Two ways it ends with nothing

Where nothing of the position is left, there is nothing to protect and no replacement goes up.

Where what is left falls under the venue's smallest size, or its smallest value, the same: the pair is gone and none replaces it.

## Up, or unknown

A replacement whose send fails is looked for by name. Found resting, it stands. Found and marked rejected by the venue, the position counts as unprotected. Any answer the query cannot give — the venue not having it included — leaves the pair unknown for the watch.

One that comes back already ended is also left unknown rather than marked resting: it guards nothing, whatever its name suggests.

## Related

- [Protection](protection.md)
- [When protection is put up again](when-protection-is-put-up-again.md)
- [When protection is lost](when-protection-is-lost.md)

---

Created 2026-10-14 07:25 UTC · Last modified 2026-11-09 14:05 UTC
