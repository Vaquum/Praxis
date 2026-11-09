---
row: P75-04
baseline: 49aa659
created: 2026-11-08 22:30 UTC
modified: 2026-11-08 22:30 UTC
evidence:
  - claim: "An order is looked up by the caller's own name first, and by the venue's name only where that fails"
    source: "`replay_venue_adapter.py` 295-296, then 298-301"
  - claim: "The lookup by the venue's name walks the recorded orders and stops at the first match, the records being kept under the caller's name rather than the venue's"
    source: "`replay_venue_adapter.py` 299-301, the records keyed at 229"
  - claim: "Neither name matching raises a not-found carrying both names as they were asked"
    source: "`replay_venue_adapter.py` 303-306"
  - claim: "Asking for a linked pair always raises a not-found, nothing of the kind ever being recorded"
    source: "`replay_venue_adapter.py` 317-320"
  - claim: "Asking for the open orders always answers with none, every order being filled as it is taken"
    source: "`replay_venue_adapter.py` 329"
  - claim: "Asking for money moved in or out always answers with none"
    source: "`replay_venue_adapter.py` 393"
  - claim: "Asking for balances answers one entry per asset asked for, with nothing locked and an unheld asset read as nought"
    source: "`replay_venue_adapter.py` 338, then 340-343"
  - claim: "Asking for a symbol's rules raises a not-found where none are held, rather than answering with none"
    source: "`replay_venue_adapter.py` 398-400"
  - claim: "An order, a linked pair and a book can each raise that same kind of failure too"
    source: "`replay_venue_adapter.py` 303-306, or 317-320, or 412-413"
---
# What the replay venue answers when asked

The venue a replay trades against answers the asking side of the interface, and several of its answers are fixed.

## Looking up an order

By the caller's own name first. By the venue's name only where that fails — and that lookup walks the recorded orders and stops at the first match, the records being kept under the caller's name rather than the venue's.

So a caller that reused one of its own names has the later record under it, and the earlier one is gone from the walk as well as from the direct lookup.

Neither name matching raises a not-found carrying both names as they were asked, so a caller sees which pair it offered.

## The three fixed answers

A linked pair is never found: nothing of the kind is ever recorded, so the asking always raises.

The open orders are always none, every order being filled as it is taken.

Money moved in or out is always none.

## Balances

One entry per asset asked for, with nothing locked. An asset the account has never held reads as nought, so asking about an unknown asset gives an entry rather than a gap.

## Rules, asked two ways

Asking for a symbol's rules raises a not-found for a symbol the venue holds rules for nowhere, rather than answering with none. [The snapping](what-the-replay-venue-snaps-a-quantity-to.md) meets the same absence and passes the quantity through unchanged instead.

An order, a linked pair and a book can each raise that same kind of failure, so it is not the only asking that can.

## Related

- [Replay](replay.md)
- [What the replay venue snaps a quantity to](what-the-replay-venue-snaps-a-quantity-to.md)
