---
row: P4-51
baseline: 49aa659
created: 2026-10-14 08:25 UTC
modified: 2026-10-14 08:25 UTC
evidence:
  - claim: "The venue is asked from the last movement seen, less a week"
    source: "`trading.py` 1138 and 1140, the week at 60"
  - claim: "The window never reaches back past the moment the account was registered"
    source: "`trading.py` 1142-1143, that moment taken at 1104-1105 and kept at 1111-1113"
  - claim: "An account with a movement already recorded starts from that one instead"
    source: "`trading.py` 1115-1116"
  - claim: "An account registered with no record of it starts from now"
    source: "`trading.py` 1111-1113"
  - claim: "The mark only moves where every movement that had to be handed over was"
    source: "`trading.py` 1186-1187 against 1190-1192"
  - claim: "A movement in anything but the quote asset is passed over and still carries the mark forward"
    source: "`trading.py` 1159-1160 against 1190-1192"
  - claim: "A deposit is posted as money in against contributions, and a withdrawal the other way"
    source: "`praxis/core/account_ledger.py` 266-271 and 273-278"
---
# The window a movement is found in

Praxis asks the venue for money that moved into or out of the account, and the stretch of time it asks about is bounded at both ends. The far end is the moment the account was taken on, and nothing before it is ever found.

## Where the window starts

The venue is asked from the last movement already recorded, less a week of overlap, so a movement that arrived late is still picked up. An account with nothing recorded yet is asked from the moment it was registered.

That registered moment is also a floor: where the overlap would reach back past it, the window is pulled forward to it. So a deposit made before the account was taken on sits outside every window there will ever be, and is never booked — the account's books begin when the account does.

An account registered with no record of that moment is asked from now, which is the same floor drawn at the latest possible point.

## When the mark moves

The mark only moves on where every movement that had to be handed over was. One handover that fails holds it back, so the next pass asks over the same stretch again.

Movements in anything but the quote asset are passed over without a handover, and still carry the mark forward with them.

## What a movement does to the books

A deposit is posted as money in against contributions, and a withdrawal the same two accounts the other way round. The money is the account's; the contribution is what was put in to get it, which is what keeps [the money record](the-money-ledger.md) balanced.

## Related

- [What a reconciliation tells Nexus](what-a-reconciliation-tells-nexus.md)
- [The money ledger](the-money-ledger.md)
- [Reports that do not get through](reports-that-do-not-get-through.md)

---

Created 2026-10-14 08:25 UTC · Last modified 2026-10-14 08:25 UTC
