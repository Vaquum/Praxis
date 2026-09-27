---
row: P2-45
baseline: 49aa659
created: 2026-09-27 09:42 UTC
modified: 2026-09-27 13:52 UTC
evidence:
  - claim: "Two kinds of refusal leave the outcome undecided on an ordinary send"
    source: "`execution_manager.py` 4282-4291"
  - claim: "One of those two gathers lost connections, timeouts, unparsable replies and server errors alike"
    source: "`binance_adapter.py` 660-662 and 1635-1643"
  - claim: "Every other venue failure is recorded failed"
    source: "`execution_manager.py` 4292-4295"
  - claim: "An order closing a position out asks after every kind"
    source: "`execution_manager.py` 7791-7813"
  - claim: "A status Praxis does not recognise is recorded as a failure by most senders"
    source: "`execution_manager.py` 4296-4299, raised at `binance_adapter.py` 897"
  - claim: "A first protective send lets it through instead"
    source: "`execution_manager.py` 4979-5015"
  - claim: "A finished pair whose orders both report unknown statuses is read as cancelled"
    source: "`binance_adapter.py` 983-994"
  - claim: "Met while asking after an order, it is handled by none of that"
    source: "`execution_manager.py` 5533-5542"
  - claim: "From one slice of work being fed out, the whole of that work ends refused"
    source: "`execution_manager.py` 5866-5882"
---
# What a refusal says

A refusal arrives as a named kind, and the kind decides what happens. On an ordinary send, two kinds leave the outcome undecided, and Praxis [asks the venue what became of the order](when-a-send-is-unclear.md). Each covers more than its name suggests: one gathers lost connections, timeouts, replies that will not parse and server errors alike. Every other kind is recorded as failed. An order closing a position out asks after all of them.

A status Praxis does not recognise is recorded as a failure by most senders. An order closing a position out, and a first protective send, let it through instead.

For a linked pair the venue calls finished, a pair whose two orders both report statuses Praxis does not know is read as cancelled. Called anything else, the two orders' statuses go unread.

The same unrecognised status met while asking after an order is handled by none of that, because it arises inside the asking itself, and [ends with nothing reported](a-reply-that-cannot-be-read.md). What follows depends on who was asking: from a plain send nothing is reported; from one slice of work being fed out, the whole of that work ends refused.

## Related

- [What a venue is](what-a-venue-is.md)
- [When a send's outcome is unknown](when-a-send-is-unclear.md)
