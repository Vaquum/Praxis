---
row: P4-31
baseline: 49aa659
created: 2026-10-03 09:39 UTC
modified: 2026-10-03 10:02 UTC
evidence:
  - claim: "The books' figure for each asset is compared against what the venue holds, free and locked together"
    source: "`trading.py` 1232, 1253 and 1255-1257"
  - claim: "A difference at or above minus the tolerance is left alone, so the boundary itself is not reported"
    source: "`trading.py` 1260 against the table at 63-66"
  - claim: "A surplus clears the difference remembered for that asset"
    source: "`trading.py` 1261"
  - claim: "The same difference again is passed over, by remembering the exact figure"
    source: "`trading.py` 1264-1265"
  - claim: "The report is named from the account, the asset and the exact difference"
    source: "`trading.py` 1274"
  - claim: "The comparison is abandoned while news from the venue is still queued"
    source: "`trading.py` 1229-1230"
  - claim: "It is abandoned again after the venue answers, for that reason or because the books' figures moved meanwhile"
    source: "`trading.py` 1245-1249"
---
# When a balance shortfall is reported

A **shortfall** is the venue holding less of an asset than the books say. Praxis compares the two for the quote asset and the coin, free and locked together, and [tells Nexus](what-a-reconciliation-tells-nexus.md) where one is found.

## Only one direction, past a tolerance

A surplus is passed over. Each asset also carries a tolerance — a hundredth of a unit of the quote asset, one hundred-millionth of a coin — and a difference at or inside it is left alone, the boundary included.

A surplus also clears the difference remembered for that asset. [A report still waiting to be handed over](reports-that-do-not-get-through.md) is kept apart from that memory.

## Only once per difference

The exact difference is remembered, so the same one found again is passed over.

The report's own name is built from the account, the asset and that exact difference. A shortfall that changes — deepening or easing, so long as it stays past the tolerance — is therefore a different report.

## Not while the books are behind

The comparison is abandoned while news from the venue is still queued, since the ledger lags [the record](the-event-spine.md) until [the account's worker](how-waiting-work-is-drained.md) catches up. It is abandoned again after the venue answers — for that reason, or because the books' figures moved while the venue was being asked.

## Related

- [What a reconciliation tells Nexus](what-a-reconciliation-tells-nexus.md)
- [Reports that do not get through](reports-that-do-not-get-through.md)
- [Holdings](holdings.md)
