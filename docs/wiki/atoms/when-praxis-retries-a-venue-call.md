---
row: P4-53
baseline: 49aa659
created: 2026-10-14 10:10 UTC
modified: 2026-10-14 10:10 UTC
evidence:
  - claim: "A call marked repeatable gets three attempts, and one that is not gets a single attempt"
    source: "`binance_adapter.py` 580, the three at 96"
  - claim: "Placing an order is sent as not repeatable"
    source: "`binance_adapter.py` 1629-1630"
  - claim: "Every attempt takes a slot of its own from the allowance"
    source: "`binance_adapter.py` 588 inside the loop at 582"
  - claim: "A transient failure waits a random stretch that doubles, and three attempts allow two waits"
    source: "`binance_adapter.py` 599-604 under the loop at 582, the half second at 97 and the three at 96"
  - claim: "Only the answer meaning too many requests is waited on, and any other escapes at once"
    source: "`binance_adapter.py` 606-608, the one at 85"
  - claim: "That answer's own waiting time is honoured where it gives one, and the doubling stretch stands in otherwise"
    source: "`binance_adapter.py` 609"
  - claim: "The last attempt raises rather than waiting again"
    source: "`binance_adapter.py` 597-598"
---
# When Praxis retries a venue call

A call to [the venue](what-a-venue-is.md) that fails is sometimes sent again and sometimes not, and which it is turns on whether sending it twice could do the work twice.

## Which calls repeat

A call marked repeatable gets three attempts. Everything else gets one.

Placing an order is sent as not repeatable, because a send that failed on the way out may still have reached the venue — so a second attempt could leave two orders where one was asked for. [What Praxis does instead](when-a-send-is-unclear.md) is ask the venue what became of the name it used.

## How long it waits

A failure that looks temporary waits a random stretch before the next attempt, drawn from a window that doubles: up to half a second before the second attempt, up to one before the third. Three attempts allow two waits, so the window never widens past that.

Being turned away for calling too often is handled separately, and only the one answer that means too many requests is waited on at all — any other escapes immediately. Where that answer names its own waiting time, Praxis waits exactly that, and otherwise falls back to the doubling window.

The last attempt never waits — it raises, and the caller deals with it.

## What the waiting costs

Each attempt takes a slot of its own from [the allowance on calls](holding-back-sends.md). A call retried twice has spent three slots, so a venue answering slowly drains the allowance faster than the number of calls Praxis means to make suggests.

## Related

- [Holding back sends](holding-back-sends.md)
- [When a send's outcome is unknown](when-a-send-is-unclear.md)
- [What a refusal says](what-a-refusal-says.md)

---

Created 2026-10-14 10:10 UTC · Last modified 2026-10-14 10:10 UTC
