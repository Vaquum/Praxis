---
row: P1-02
baseline: 49aa659
created: 2026-09-20 16:25 UTC
modified: 2026-09-25 18:14 UTC
evidence:
  - claim: "Every other kind is routed elsewhere before this path"
    source: "any of the arms at `execution_manager.py` 3994-4007, with a defensive refusal for anything that still arrives at 4170-4188"
  - claim: "A supplied name is refused if already in use"
    source: "`execution_manager.py` 3452-3457"
  - claim: "A name is generated only where none was supplied"
    source: "`execution_manager.py` 3445-3446, otherwise generated at 3459"
  - claim: "The accept is written down before the work is queued"
    source: "`execution_manager.py` 3515-3525, queued at 3550"
  - claim: "The request name comes back on both paths"
    source: "`execution_manager.py` 3547 for a died account, 3582 otherwise"
  - claim: "An account that died across that write ends the work unqueued"
    source: "`execution_manager.py` 3531-3547"
  - claim: "A cancellation that arrived while waiting ends the work unsent"
    source: "`execution_manager.py` 4154-4168"
  - claim: "The likely price is attempted, and only a market order with a host-wide maximum set can be turned back"
    source: "`execution_manager.py` 4192-4197, either sizing at 4198-4205; the maximum stored at 680 and read with the order type at 4064-4065"
  - claim: "A figure past that maximum turns the order back"
    source: "measured at `execution_manager.py` 4081-4086, turned back at 4098 rather than let through at 4087-4088, applied at 4232-4240"
  - claim: "No figure at all turns it back too"
    source: "the reason given at `execution_manager.py` 4067-4079, whether the book request failed at 4222-4228 or the book it returned could not be priced, from either sizing at 4200-4202 or 4204-4205, logged at 4207-4212"
  - claim: "Only an order left pending or partly filled is measured against its deadline"
    source: "`execution_manager.py` 4411-4414, the status assigned just above by either the quote arm at 4395-4400 or the quantity arm at 4401-4408"
  - claim: "A deadline already past then cancels the order and reports it expired"
    source: "the moment stored at either `execution_manager.py` 4281 or 4291 and compared at 4414, marked at 4415-4417, cancelled by either 4419-4424 or 4426-4430, reported at 4446-4448"
  - claim: "The order is named and the intent written down before the order is sent"
    source: "`execution_manager.py` 4242-4265, sent at 4269-4280"
  - claim: "The book is asked for before that record exists, whether or not an answer comes back"
    source: "`execution_manager.py` 4192-4197, a failure to reach it or to read its reply wrapped at `binance_adapter.py` 2277-2279 and caught at `execution_manager.py` 4222-4228"
  - claim: "Two wrapped failures are chased up"
    source: "`execution_manager.py` 4282-4286"
  - claim: "Other venue errors are recorded failed on the spot, as is any value the adapter refuses, including an unrecognised status on the submit reply"
    source: "either `execution_manager.py` 4292-4295 or 4296-4299, the latter taking what `binance_adapter.py` 893-897 raises by way of 950"
  - claim: "The chase usually either adopts the order or writes the send off"
    source: "either `execution_manager.py` 4290-4291 or 4287-4288"
  - claim: "A lookup reply it cannot read reaches neither, leaving only a log"
    source: "raised in `binance_adapter.py` 1027-1039, escaping `execution_manager.py` 5518-5542, logged at 4012-4019"
  - claim: "On a single order, a lookup reply whose status or fields cannot be read reaches neither, and no outcome is recorded"
    source: "raised in `binance_adapter.py` 1027-1039, or an unrecognised status by way of 1033 into 893-897; the lookup runs inside `execution_manager.py` 4282-4286 so 4296-4299 never sees it, and it escapes either 5524-5532 or 5533-5542, logged at 4012-4019, the intent at 4264 standing alone"
  - claim: "A linked pair takes its own lookup, where a venue error on the list is written off"
    source: "`execution_manager.py` 5513-5516, caught at 5595-5604, written off at 4287-4288"
  - claim: "A pair whose list or leg fields cannot be read escapes that too, and no outcome is recorded"
    source: "raised at `binance_adapter.py` 1056-1058, 1071-1074 or 1027-1039, outside `execution_manager.py` 5595-5604 and 5677-5688, logged at 4012-4019"
  - claim: "A list that comes back with no orders is caught instead, and the send written off"
    source: "raised at `binance_adapter.py` 1063-1068, caught at `execution_manager.py` 5595-5604, written off at 4287-4288"
  - claim: "On a single order, a lookup body that will not parse is handled instead, and the send written off"
    source: "a success body wrapped at `binance_adapter.py` 660-662 and raised at 680, or an error body given code -1 at 1143-1145 and raised at 1151-1152, caught at `execution_manager.py` 5533-5542, written off at 4287-4288"
---
# Order placement

Placing an order happens in two stages separated in time: **submitting**, which records the work and returns straight away, and **sending**, which reaches the venue on a later pass of the worker.

This covers a plain single order. Work asking to be fed out over time, laddered, given a separate display size, or wrapped with protection is queued the same way but carried out along its own path.

## Submitting

Work arrives carrying a [trade name](what-a-trade-is.md), and gets a [request name](what-a-trade-is.md) too: one supplied with it, or one Praxis generates.

Several gates can [turn it away](what-turns-work-away.md) first. Otherwise it writes down the accept. If the account died across that write the work ends there unqueued; otherwise it is queued. Both those paths return the request name, and nothing has reached the venue.

## Sending

[The account's worker](how-waiting-work-is-drained.md) takes the work off the queue later. It first drops the work if [a cancellation](how-a-trade-is-cancelled.md) arrived while it waited.

Otherwise it tries to work out what the order would likely average at the venue. Only a market order can be turned back on that answer, or on the absence of one: see [the likely-price check](how-the-likely-price-is-checked.md).

Only then does it name the order, write the intent down, and call the venue. The writing-down comes first, so a record naming the order exists before the order goes out. An order left pending or partly filled past its [deadline](deadlines.md) has a cancel attempted and is reported expired — unless that cancel's reply [lacks a field or carries an unfamiliar status](a-reply-that-cannot-be-read.md), which ends it with nothing reported.

Some failures are [chased up with the venue](when-a-send-is-unclear.md) before the send is called failed; others are recorded failed on the spot; and some end with no outcome at all, leaving whatever was already written.

## Related

- [When a send's outcome is unknown](when-a-send-is-unclear.md)
- [Trades, requests and orders](what-a-trade-is.md)
- [The likely-price check](how-the-likely-price-is-checked.md)
- [What turns work away before it is queued](what-turns-work-away.md)
- [The account worker](how-waiting-work-is-drained.md)
