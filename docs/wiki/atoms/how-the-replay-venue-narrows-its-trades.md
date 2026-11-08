---
row: P75-05
baseline: 49aa659
created: 2026-11-13 06:30 UTC
modified: 2026-11-13 06:30 UTC
evidence:
  - claim: "A cursor given together with either end of a window is refused before any trade is read"
    source: "`replay_venue_adapter.py` 357-359"
  - claim: "The trades of one account are narrowed to the symbol asked for first"
    source: "`replay_venue_adapter.py` 361-365"
  - claim: "A cursor keeps the trades whose number stands at or above it, the number being read out of the trade's own name"
    source: "`replay_venue_adapter.py` 367-371, the number read at 60-63"
  - claim: "Each end of a window keeps the trades at or inside it, so a trade stamped exactly at either end is kept"
    source: "`replay_venue_adapter.py` 373-374, and 376-377"
  - claim: "A limit is applied last, keeping the first of what is left, which is the earliest recorded of them"
    source: "`replay_venue_adapter.py` 379-380, the recording appending at 253"
  - claim: "An account the venue has no trades for answers with none rather than raising"
    source: "`replay_venue_adapter.py` 363, reading with a default"
  - claim: "Taking an account back removes its balances and leaves its trades, so an account no longer registered still answers with them"
    source: "`replay_venue_adapter.py` 121 removing one book, against 253 writing the other"
---
# How the replay venue narrows its trades

Asking the venue a replay trades against for its trades applies up to four narrowings, in a fixed order.

## The one combination refused

A cursor given together with either end of a window. That is refused before any trade is read, so the two ways of narrowing cannot be mixed.

## The order

The account's trades are narrowed to the symbol asked for.

A cursor then keeps those whose number stands at or above it. The number is read out of the trade's own name rather than stored beside it.

Each end of a window keeps the trades at or inside it, so a trade stamped exactly at either end is kept.

A limit is applied last.

## What the limit keeps

The first of what is left, which is the earliest recorded of them — the trades being appended as they are made. Nothing here sorts them by their moment, so the order is the order of recording.

## An account with no trades

Answers with none. The reading uses a default, so an account the venue has never seen looks like one that has not traded.

Taking an account back removes its balances and leaves its trades. So an account no longer registered still answers with everything it traded, while an order for it would be refused for being unknown.

## Related

- [What the replay venue answers when asked](what-the-replay-venue-answers-when-asked.md)
- [Replay](replay.md)
