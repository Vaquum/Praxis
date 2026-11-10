---
row: P116-02
baseline: 49aa659
created: 2026-11-09 09:06 UTC
modified: 2026-11-10 13:57 UTC
evidence:
  - claim: "The adapter is built holding a lock of its own for the health figures"
    source: "`binance_adapter.py` 312"
  - claim: "A tracker is made at construction for each account the adapter was handed credentials for"
    source: "`binance_adapter.py` 297, then 308-310"
  - claim: "Reading the clock drift takes that lock for the read alone"
    source: "`binance_adapter.py` 2341, then 2342"
  - claim: "A health answer takes it for the tracker lookup and the drift, then lets it go"
    source: "`binance_adapter.py` 2390, then 2391, then 2392"
  - claim: "The allowance in use is reckoned after the lock is let go"
    source: "`binance_adapter.py` 2394 past 2390-2392"
  - claim: "An account with no tracker is answered with a snapshot carrying the allowance and the drift alone"
    source: "`binance_adapter.py` 2395 into 2396-2399, the other three figures standing at their defaults at `health_snapshot.py` 33-35"
  - claim: "Otherwise the tracker is asked for the answer, those two figures handed to it"
    source: "`binance_adapter.py` 2401-2403"
  - claim: "That same lock is taken to add a tracker when an account registers, and to drop it when one leaves"
    source: "`binance_adapter.py` 445 into 446, or 461 into 462"
  - claim: "Recording what a request cost takes it for the lookup alone too"
    source: "`binance_adapter.py` 2309, then 2310"
---
# Which health figures are read under the lock

The adapter keeps one lock of its own over its health figures, and every reading of them holds it for the lookup and lets it go before the answer is put together.

## What the lock covers

Reading the clock drift takes it for the read alone. A health answer takes it for two things together — finding the account's tracker, and reading the drift — and then lets it go. Recording what a request cost takes it for the lookup alone too.

## What is reckoned outside it

The share of the venue's allowance in use. It is worked out after the lock has gone, from figures the allowance headers write, so the drift and the allowance in one answer are read at two moments with a gap between them.

## The two answers

An account the adapter holds no tracker for is answered with a snapshot carrying the allowance and the drift alone, its other three figures standing at the nought each defaults to. A tracker is made at construction for each account whose credentials the adapter was handed.

Otherwise the tracker is asked for the answer, those two figures handed to it, and whatever it keeps is added to them.

## What else the lock holds

Adding a tracker when an account registers, and dropping it when one leaves. So a reading and an account arriving or going cannot overlap: the reading finds a tracker or finds none.

## Related

- [Health](health.md)
- [How the adapter reckons its headroom](how-the-adapter-reckons-its-headroom.md)
- [What the allowance headers are trusted for](what-the-allowance-headers-are-trusted-for.md)
