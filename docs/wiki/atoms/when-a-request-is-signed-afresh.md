---
row: P113-01
baseline: 49aa659
created: 2026-11-09 08:42 UTC
modified: 2026-11-09 08:42 UTC
evidence:
  - claim: "A session and the account's credentials are taken once, before any request is built"
    source: "`binance_adapter.py` 720, then 721"
  - claim: "The key travels in a header made once from those credentials"
    source: "`binance_adapter.py` 722"
  - claim: "The building of a request is handed over as something to call rather than as a request already made"
    source: "`binance_adapter.py` 732-734, which passes the building rather than a built request"
  - claim: "Each call of it signs the parameters afresh and builds the address from that signing"
    source: "`binance_adapter.py` 725, then 726-730"
  - claim: "So every retry carries a moment and a seal of its own, taken when that attempt is made"
    source: "`binance_adapter.py` 725, reached each time the retry calls what it was handed at 732-734"
---
# When a request is signed afresh

A signed request is not built once and sent repeatedly. The building is handed to the retry as something to call, and each call signs again.

## What is taken once

A session, and the account's credentials. The key travels in a header made once from those credentials.

So the key is fixed for the whole of the attempting, and a caller whose credentials change mid-flight is not affected by it.

## What is made per attempt

The signing, and the address built from it. Each call of the handed-over building signs the parameters afresh.

So every retry carries [a moment and a seal of its own](what-signing-a-request-adds.md), taken when that attempt is made. A retry after a long wait is not sending a stale moment, which is what would happen had the address been built once and reused.

## Why it is handed over rather than built

Because the retry decides how many times to call it, and each call must produce a request the venue will accept. Handing over a built request would mean either one moment for every attempt or the retry doing the signing itself.

The arrangement puts the signing where the attempt is, and leaves the retry knowing nothing about signing at all.

## Related

- [What signing a request adds](what-signing-a-request-adds.md)
- [Which failures a retry counts as healthy](which-failures-a-retry-counts-as-healthy.md)
