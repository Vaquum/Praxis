---
row: P106-02
baseline: 49aa659
created: 2026-11-09 08:12 UTC
modified: 2026-11-09 08:12 UTC
evidence:
  - claim: "The account's stored events are replayed into the manager before anything else happens"
    source: "`praxis/trading.py` 548, ahead of 549"
  - claim: "The account is then recorded on the spine, and its orphaned commands reconciled against those same events"
    source: "`praxis/trading.py` 549, then 550-552"
  - claim: "The symbols whose rules are loaded are the active ones, the bootstrap's, and every one a bracket in the stored events names"
    source: "`praxis/trading.py` 554, then 555, then 556-560"
  - claim: "The rules are loaded only where that gathering found something, and in sorted order"
    source: "`praxis/trading.py` 561 into 562"
  - claim: "Protection remediations and the fund cursor are seeded from the stored events"
    source: "`praxis/trading.py` 564, then 565"
  - claim: "Whether the account is ready is what the sweep for stray venue orders answered"
    source: "`praxis/trading.py` 546, set at 567"
  - claim: "External events are drained and incomplete flattens recovered before readiness is settled"
    source: "`praxis/trading.py` 598, then 600-602, ahead of 606"
  - claim: "An account the manager calls poisoned is held back however the sweep answered"
    source: "`praxis/trading.py` 604, weighed at 606"
---
# What an account's startup does in order

Starting one account replays what the spine holds, loads what the venue needs, and decides at the end whether the account may trade.

## The replay first

The account's stored events are replayed into the manager before anything else happens. So everything after works against a manager that already knows the account's history.

The account is then recorded on the spine, and its orphaned commands reconciled against those same events.

## Which symbols get their rules

The active ones, the bootstrap's, and every one a bracket in the stored events names. The rules are loaded only where that gathering found something, and in sorted order.

The third source is the careful one: a bracket from a previous run names a symbol the account may no longer be active in, and its rules are needed to finish that bracket.

## What else the stored events seed

Protection remediations, and the fund cursor.

## How readiness is decided

Whether the account is ready is what [the sweep for stray venue orders](what-the-sweep-for-stray-venue-orders-looks-for.md) answered. External events are drained and incomplete flattens recovered before that readiness is settled.

An account the manager calls poisoned is held back however the sweep answered. So readiness needs both: nothing stray at the venue, and nothing poisoned here.

## Related

- [What the sweep for stray venue orders looks for](what-the-sweep-for-stray-venue-orders-looks-for.md)
- [What a failed start undoes](what-a-failed-start-undoes.md)
