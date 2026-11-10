---
row: N3-01
baseline: 49aa659
created: 2026-10-22 15:00 UTC
modified: 2026-10-23 07:08 UTC
evidence:
  - claim: "A close meant to take the whole position whose finishing fill leaves some of it moves what is left into the account's dust, sets the size to nought, and removes the position"
    source: "`nexus/infrastructure/praxis_connector/outcome_processor.py` 563 into 576-580 into 594-595, a size of nought being what closes it at `nexus/core/domain/position.py` 94"
  - claim: "That road is taken only where the fill finished the order, the close was meant to be whole, and something is left; a part-fill of the same close is read by the same pass and leaves the remainder alone"
    source: "`nexus/infrastructure/praxis_connector/outcome_processor.py` 562-566, both kinds reaching the pass at 154-157"
  - claim: "Where the fill finished the order, the close was meant to be whole, and something is left"
    source: "`nexus/infrastructure/praxis_connector/outcome_processor.py` 562-566"
  - claim: "The same road is taken with no order placed where making the sale ready for the venue refuses it for any reason at all, the close was meant to be whole, and the position has nothing pending on it"
    source: "`praxis/launcher.py` 1323 and 1339-1342 into 1363-1367, returning before an order is built at 1369, the reasons at `praxis/infrastructure/binance_adapter.py` 1361-1376 and 1383-1420"
  - claim: "That second road moves what is left, sets the size to nought and removes the position"
    source: "`nexus/infrastructure/praxis_connector/outcome_processor.py` 696-702, closed at `nexus/core/domain/position.py` 94"
  - claim: "It is dropped on a repeat of the key its caller supplies, and answers no"
    source: "`nexus/infrastructure/praxis_connector/outcome_processor.py` 676-682"
  - claim: "The key is marked used before the position is looked for, so a close for one that is not there answers no with the key spent"
    source: "`nexus/infrastructure/praxis_connector/outcome_processor.py` 684 against 686-694"
  - claim: "Both roads write the base asset alone"
    source: "`nexus/infrastructure/praxis_connector/outcome_processor.py` 577-579 and 698-700"
  - claim: "Beyond the two places that write it, the dust is named in three: where it is declared, where it is checked for shape, and where it is written to the snapshot and read back"
    source: "`nexus/core/domain/instance_state.py` 80 and 105-118, `nexus/infrastructure/wal_codec.py` 77-93 and 134-149"
---
# Where a position's last scraps go

A scrap is what a finishing sale leaves of a position, and it goes to the account's dust: a running total per symbol.

## The sale that leaves some behind

A sale meant to take the whole position can come back having taken less. Where the fill finished the order, the close was meant to be whole, and something is still there, what is left is added to the dust for that symbol and the size set to nought — which closes the position, so it is removed. A part-fill of the same close goes through the same pass and leaves the remainder where it is.

## The sale that never happens

Where making the sale ready for the venue refuses it — too small for its filters, or a size or reference price that is not a finite number — the same thing happens with no order placed — provided the close was meant to be whole and the position has nothing pending on it. The remainder goes to the dust and the position is removed.

That road is asked for by name, with a key the caller supplies, and a repeat of the key is dropped. The key is marked used before the position is looked for, so a close naming one that is not there answers no and spends the key doing it.

Both roads write the coin. What they leave of the money is [a seam of its own](what-a-dusted-scrap-leaves-behind.md).

## What the dust is worth

Beyond the two lines that add to it, the dust is named in three places: where it is declared, where it is checked for shape with the rest of the account's record, and where it is written to the snapshot and read back.

## Related

- [What an exit outcome changes](what-an-exit-outcome-changes.md)
- [What a boot rebuilds from the positions](what-a-boot-rebuilds-from-the-positions.md)

---

Created 2026-10-22 15:00 UTC · Last modified 2026-10-23 07:08 UTC
