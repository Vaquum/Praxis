---
row: P4-06
baseline: 49aa659
created: 2026-10-03 09:37 UTC
modified: 2026-10-03 10:02 UTC
evidence:
  - claim: "The two periodic detectors send money moved into or out of the account, and a balance that falls short"
    source: "`trading.py` 1162-1168 and 1271-1278, routed at `launcher.py` 3007-3025"
  - claim: "Squaring the books also recovers fills and endings, which cross as outcomes instead"
    source: "`trading.py` 1052-1071 and 1663-1690 into `execution_manager.py` 10704-10741, routed at `launcher.py` 2973-3005"
  - claim: "Nexus asks the other way during its own startup squaring, and a snapshot of positions goes back"
    source: "Nexus `sequencer.py` 363 into `praxis_outbound.py` 434-438, wired at `launcher.py` 458"
  - claim: "Only movements in the quote asset become the first kind; anything else is passed over there"
    source: "`trading.py` 1159-1160"
  - claim: "Two assets are compared, the quote and the base"
    source: "`account_ledger.py` 178-181, read at `trading.py` 1232"
  - claim: "A movement in the base asset is reported only where it leaves a shortfall past the tolerance"
    source: "`trading.py` 1255-1262"
  - claim: "Each finding is re-keyed field by field into the kind Nexus takes"
    source: "`reconciliation_translate.py` 54-60 and 76-83"
  - claim: "Both have their moment restamped to exactly the zone Nexus wants"
    source: "`reconciliation_translate.py` 56 and 78"
  - claim: "Nexus tests that zone by identity, where Praxis asks for a moment that carries a zone and an offset"
    source: "Nexus `fund_transaction.py` 49 and `reconciliation_mismatch.py` 54, against `events.py` 115 reached from 1665 and 1709"
  - claim: "A movement is written down before it is handed over"
    source: "`trading.py` 1170 ahead of 1180"
  - claim: "The record keeps one row per epoch, account and movement name, so a re-found movement is written once"
    source: "`execution_manager.py` 3209-3214 and 3233-3240 into `event_spine.py` 1072-1092, the key at 176-177"
  - claim: "A handover that fails stops the walk and holds the mark back, so the same ground is covered next time"
    source: "`trading.py` 1179-1193"
---
# What a reconciliation tells Nexus

Praxis squares its own books against the venue. Its two periodic detectors send Nexus money that moved into or out of the [account](what-an-account-is.md), and [a balance that falls short](when-a-balance-shortfall-is-reported.md) of what the books expect.

The same work also recovers [fills](what-a-fill-is.md) and endings the feed missed, which [cross as outcomes](how-an-outcome-crosses-back.md) rather than as findings.

Traffic goes the other way too. Nexus asks Praxis for its positions during its own startup squaring, and a snapshot goes back in answer.

## Which finding a movement becomes

Only movements in the quote asset — the money the account's capital is counted in — become the first kind.

Two assets are compared: that quote asset and the coin traded against it. A movement in the coin is seen only where it leaves a shortfall past the tolerance for that asset, so a deposit putting the account ahead of its books is passed over entirely.

## Re-keying

Nexus has its own kinds bearing the same names and fields, which are separate things to Python all the same. Each finding is re-keyed field by field.

Both have their moment restamped to exactly the zone Nexus wants. Nexus tests that zone by identity — it must be that one object — where Praxis asks for a moment carrying a zone and an offset. A moment from the venue can satisfy the one and fail the other, so the restamp relabels the instant rather than moving it.

## Written first

A movement is written to [the record](the-event-spine.md) before it is handed over, and the record keeps one row per epoch, account and movement name — so a movement found twice is written once.

A handover that fails stops the walk and holds back the mark of how far it got.

## Related

- [When a balance shortfall is reported](when-a-balance-shortfall-is-reported.md)
- [Backfilling missed trades](backfilling-missed-trades.md)
