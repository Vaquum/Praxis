---
row: P158-02
baseline: 49aa659
created: 2026-11-09 12:21 UTC
modified: 2026-11-09 12:21 UTC
evidence:
  - claim: "The pass looks the account up and ends there where the manager holds no such account"
    source: "`execution_manager.py` 9829, then 9830 into 9831"
  - claim: "It walks a copy of the account's brackets"
    source: "`execution_manager.py` 9833"
  - claim: "A bracket carrying no stamped moment is passed over, so the stamp alone decides which brackets are picked up and the standing of the change is never read"
    source: "`execution_manager.py` 9834 into 9835"
  - claim: "Each bracket the stamp names is driven again with nothing given for the cancelled pair's venue name"
    source: "`execution_manager.py` 9837"
  - claim: "Where that name is not given, the name recorded against the old pair stands in for it, and an empty one where no record of the pair is held"
    source: "`execution_manager.py` 9599-9602"
  - claim: "The stamp goes on the first time the old pair's fills will not reconcile, and the standing is parked at cancel-confirmed beside it"
    source: "`execution_manager.py` 9572 into 9573, then 9577"
  - claim: "It comes off once those fills do reconcile"
    source: "`execution_manager.py` 9596"
  - claim: "The road where the asking itself fails leaves the standing unknown and clears the stamp"
    source: "`execution_manager.py` 9553, then 9555"
---
# What picks a held protection change up again

A change to a [protective pair](protection.md) that stopped halfway, because the fills of the pair it cancelled would not reconcile, is driven again by a scan over the account's brackets.

## What the scan reads

It looks the account up and ends there where the manager holds no such account, then walks a copy of that account's brackets.

A bracket carrying no stamped moment is passed over. The stamp alone decides which brackets are picked up: the standing the change sits at is never read here, though the road that stamps a bracket parks that standing at cancel-confirmed in the same breath.

Each bracket the stamp names is driven again, with nothing given for the cancelled pair's venue name. The driving needs that name to write the pair off, and takes the one recorded against the old pair where it is given none — an empty name where no record of the pair is held at all.

## When the stamp goes on and comes off

It goes on the first time the old pair's fills will not reconcile, and comes off once they do.

One road clears it while leaving the change halfway: where the asking after those fills fails outright, the standing is left unknown and the stamp cleared. That bracket is off this scan's list from then on, and [the watch over protection in doubt](when-protection-is-lost.md) is what reaches it instead.

## Related

- [How protection's prices are changed](how-protections-prices-are-changed.md)
- [When protection is lost](when-protection-is-lost.md)
- [Protection](protection.md)
