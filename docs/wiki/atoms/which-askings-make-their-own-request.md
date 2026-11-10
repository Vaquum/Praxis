---
row: P116-03
baseline: 49aa659
created: 2026-11-09 09:06 UTC
modified: 2026-11-09 09:06 UTC
evidence:
  - claim: "Each of the three addresses the adapter is built with has a trailing slash taken off"
    source: "`binance_adapter.py` 294, then 295, then 296"
  - claim: "The allowance for venue work is built once, at ten a second holding ten"
    source: "`binance_adapter.py` 304, the two figures at 99-100"
  - claim: "The rules asking takes the session, waits its turn against that allowance, then makes its own request with a path joined straight onto the stored address"
    source: "`binance_adapter.py` 2170, then 2173, then 2174-2178"
  - claim: "The depth asking does the same"
    source: "`binance_adapter.py` 2260, then 2263, then 2264-2267"
  - claim: "The signed road instead hands a request to the retrying to build, which takes a slot of its own for every attempt it makes"
    source: "`binance_adapter.py` 732-734, the slot at 588 inside the loop at 582"
  - claim: "The making of the request sits under a try in each of the two"
    source: "`binance_adapter.py` 2172, and 2262"
  - claim: "The reading of the answer sits under a second try, begun after the first has ended"
    source: "`binance_adapter.py` 2219 past 2182-2189, and 2281 past 2272-2279"
  - claim: "A venue failure raised while the answer is weighed is let past by a raise that adds nothing"
    source: "`binance_adapter.py` 2185-2186, and 2275-2276"
---
# Which askings make their own request

Two of the adapter's askings build their own request instead of handing it to the retrying, so a passing failure in either is answered to the caller rather than tried a second time.

## The two

The asking after a symbol's trading rules, and the asking after [the order book](the-order-book.md). Each takes the session, waits its turn against the allowance for venue work — ten a second, holding ten — then makes the request on that session, with a path joined straight onto the stored address.

The address makes that join safe: each of the three the adapter is built with has a trailing slash taken off, so one configured with a slash and one without reach the same place.

## What the signed road does instead

It hands a request to the retrying to build, and the retrying takes a slot of its own from the same allowance for every attempt it makes.

So the allowance is spent by the attempt on one road and by the asking on the other. The two askings take one slot each because one attempt is all either gets.

## The two tries each carries

The making of the request sits under one, and the reading of the answer under a second begun after the first has ended. A failure in the making is turned into [one of three kinds](what-the-trading-rules-asking-insists-on.md); a failure in the reading is a failure of the answer alone.

A venue failure raised while the answer is weighed is let past by a raise that adds nothing, so the kind the weighing chose is the kind the caller sees.

## Related

- [What the trading rules asking insists on](what-the-trading-rules-asking-insists-on.md)
- [When Praxis retries a venue call](when-praxis-retries-a-venue-call.md)
- [Holding back sends](holding-back-sends.md)
