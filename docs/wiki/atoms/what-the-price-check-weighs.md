---
row: N2-07
baseline: 49aa659
created: 2026-10-21 18:00 UTC
modified: 2026-10-22 19:00 UTC
reviewed: 2026-10-22 19:00 UTC
evidence:
  - claim: "The price stage weighs three things in turn: how old the book is, how wide its spread is, and how far a price sits from a reference"
    source: "`nexus/core/validator/price_stage.py` 258, 293 and 316"
  - claim: "Each runs only where a limit for it is set, so an unset limit leaves that figure unread"
    source: "`nexus/core/validator/price_stage.py` 258, 293 and 316"
  - claim: "The age is the moment the snapshot was taken less the moment on the book, refused past the limit"
    source: "`nexus/core/validator/price_stage.py` 281-289"
  - claim: "That moment is when Praxis fetched the book, taken off its own clock as the fetch returned, the venue's answer carrying no time of its own"
    source: "`praxis/infrastructure/book_cache.py` 134-136 from `praxis/infrastructure/book_poller.py` 73-77, the answer's fields at `praxis/infrastructure/venue_adapter.py` 433-436"
  - claim: "The cap on deviation is the one set for the asking strategy where there is one, and the general one otherwise"
    source: "`nexus/core/validator/price_stage.py` 312-314"
  - claim: "A deviation past that cap refuses last"
    source: "`nexus/core/validator/price_stage.py` 361-369"
  - claim: "No snapshot at all, no moment on it, or no stamp on the book each refuse alike"
    source: "`nexus/core/validator/price_stage.py` 259-270"
  - claim: "A book stamped later than the snapshot was taken refuses separately, the age being worked out only past that"
    source: "`nexus/core/validator/price_stage.py` 273-279 before 281"
  - claim: "Praxis reads the clock for that moment before it reads the book out of the cache, where a newer one may have landed in between"
    source: "`praxis/launcher.py` 3782-3788 before `praxis/infrastructure/book_cache.py` 108, the poller stamping at `praxis/infrastructure/book_poller.py` 76-77"
  - claim: "A missing spread figure refuses before the spread is weighed"
    source: "`nexus/core/validator/price_stage.py` 294-300"
  - claim: "A deviation refuses where the configured source for the reference price is missing, where the decision carries no reference price, where the snapshot's deviation or source is missing, or where the two sources disagree, none of which weighs it against the cap"
    source: "`nexus/core/validator/price_stage.py` 317-326, 327-336, 337-350 and 351-360, the cap compared only at 361"
---
# What the price check weighs

The price stage is [the check](what-each-check-weighs.md) that looks at the market rather than the account. It weighs three things in turn, and each runs only where a limit for it is set, so an unset limit leaves that figure unread.

## Three figures

How old the book is: the moment the snapshot was taken, less the moment on the book, refused past the limit. That moment is when Praxis fetched it, off its own clock as the fetch returned — the venue's answer carries no time, so the age is the wait since the fetch.

How wide its spread is, refused past its own limit.

How far a price sits from a reference, refused past a cap — the one set for the asking strategy where there is one, the general one otherwise. That comparison comes last.

## What it refuses without weighing

No snapshot at all, no moment on it, or no stamp on the book each refuse alike. A book stamped later than the snapshot refuses separately, the age being worked out past that, so it always comes out at nothing or more. Neither figure need be wrong: Praxis reads the clock before it takes the book from the cache, and a newer one may land between.

A missing spread figure refuses before the spread is weighed.

The deviation has four. The configured source for the reference price may be missing; the decision may carry none; the snapshot's own deviation or source may be missing; or the two sources may name different things. Each refuses before the deviation is weighed against the cap, which happens last.

So a decision can be stopped here for a figure's absence as readily as for one out of bounds — but only where the matching limit is set.

## Related

- [What each check weighs](what-each-check-weighs.md)
- [The checks a decision passes](the-checks-a-decision-passes.md)

---

Created 2026-10-21 18:00 UTC · Last modified 2026-10-22 19:00 UTC
