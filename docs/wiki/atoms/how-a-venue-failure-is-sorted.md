---
row: P110-01
baseline: 49aa659
created: 2026-11-14 08:30 UTC
modified: 2026-11-14 08:30 UTC
evidence:
  - claim: "Anything below the first failing status answers at once and raises nothing"
    source: "`binance_adapter.py` 1115 into 1116"
  - claim: "One status becomes a failure to authenticate, on the status alone"
    source: "`binance_adapter.py` 1118 into 1119-1120"
  - claim: "Three statuses become a rate limiting, which carries the status itself back with it"
    source: "`binance_adapter.py` 1122 into 1132-1133"
  - claim: "The wait the venue asked for is read where it is offered, kept only where it reads as a finite figure at or above nought"
    source: "`binance_adapter.py` 1123-1124, then 1126 into 1127-1128, then 1129 into 1130"
  - claim: "A reading that will not parse or overflows leaves the wait absent, the failure being suppressed rather than raised"
    source: "`binance_adapter.py` 1127, naming the two it suppresses"
  - claim: "Any status at or above the server's own range becomes a passing failure, on the status alone"
    source: "`binance_adapter.py` 1135 into 1136-1137"
  - claim: "Only what is left reads the body, for a code and a reason"
    source: "`binance_adapter.py` 1139-1142"
  - claim: "A body that will not give both leaves an unknown code and a reason naming the status"
    source: "`binance_adapter.py` 1143 into 1144-1145"
  - claim: "A code among the not-found ones becomes a not-found, and everything else becomes an order refused carrying its code and reason"
    source: "`binance_adapter.py` 1147 into 1148-1149, then 1151-1152"
---
# How a venue failure is sorted

A failing answer from the venue is sorted by its status first and only then by what its body says.

## The statuses that decide alone

One becomes a failure to authenticate. Three become a rate limiting. Anything at or above the server's own range becomes a passing failure.

None of these reads the body at all. So a venue that returns a helpful message with a server error has that message discarded, because the status already settled what kind of failure it was.

## The wait a rate limiting carries

Read where the venue offered one, and kept only where it reads as a finite figure at or above nought. A reading that will not parse, or that overflows, leaves the wait absent — the failure of the reading is suppressed rather than raised.

So a nonsense wait is treated as no wait rather than as a reason to fail differently, and the caller decides what to do with its absence.

## What reads the body

Only what is left after the statuses. The body is read for a code and a reason, and a body that will not give both leaves an unknown code and a reason naming the status.

## The last two

A code among the not-found ones becomes a not-found. Everything else becomes an order refused, carrying its code and reason onward — so the venue's own words reach the caller only on this one road.

## Related

- [What signing a request adds](what-signing-a-request-adds.md)
