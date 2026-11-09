---
row: P115-02
baseline: 49aa659
created: 2026-11-14 11:00 UTC
modified: 2026-11-14 11:00 UTC
evidence:
  - claim: "Each stated limit is walked, and any entry that is not a mapping is passed over"
    source: "`binance_adapter.py` 2476, then 2477 into 2478"
  - claim: "Four fields are read off each entry before any of them is weighed"
    source: "`binance_adapter.py` 2480, and 2481, and 2482, and 2483"
  - claim: "An entry whose figure is not a whole number, or stands at or below nought, is passed over"
    source: "`binance_adapter.py` 2485 into 2486"
  - claim: "The weight limit is adopted only from an entry naming that kind, that span and that count of spans"
    source: "`binance_adapter.py` 2488-2492 into 2493"
  - claim: "The order limit is adopted only from an entry naming its own three, which differ in all three"
    source: "`binance_adapter.py` 2495-2499 into 2500"
  - claim: "The two tests are separate, so one entry could in principle satisfy neither and nothing is adopted"
    source: "`binance_adapter.py` 2488-2492, and 2495-2499, with no answer between them"
  - claim: "Recording health takes the tracker under a lock and answers where the account has none"
    source: "`binance_adapter.py` 2309-2310, then 2311 into 2312"
  - claim: "The latency recorded is held at nought at the least, measured from the moment handed in"
    source: "`binance_adapter.py` 2314, then 2315"
---
# Which stated limits the adapter adopts

The venue states several limits and the adapter adopts two of them, each only from an entry matching three things exactly.

## What is skipped

Any entry that is not a mapping. Any entry whose figure is not a whole number, or stands at or below nought.

Four fields are read off each entry before any of them is weighed, so a malformed entry costs four readings before it is discarded.

## The two it adopts

The weight limit, only from an entry naming that kind, that span and that count of spans. The order limit, only from an entry naming its own three — which differ in all three.

The two tests are separate rather than alternatives, so an entry is weighed against both and may satisfy neither. A venue that renamed a span, or stated the same limit over a different number of them, would leave the adapter on whatever limit it already held.

## What that means for the headroom

The limits the headroom is reckoned against are only ever those the venue stated in a form this routine recognises. Everything else the venue says about its limits is read and discarded.

## Recording the health

The tracker is taken under a lock, and an account with none answers there. The latency recorded is held at nought at the least, measured from the moment handed in.

## Related

- [What the allowance headers are trusted for](what-the-allowance-headers-are-trusted-for.md)
- [How the adapter reckons its headroom](how-the-adapter-reckons-its-headroom.md)
