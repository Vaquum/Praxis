---
row: P108-03
baseline: 49aa659
created: 2026-11-09 08:25 UTC
modified: 2026-11-09 08:25 UTC
evidence:
  - claim: "Closing marks the adapter closed before it touches the session"
    source: "`binance_adapter.py` 423, ahead of 424"
  - claim: "The session is taken out of the field before it is closed, so nothing else can find it"
    source: "`binance_adapter.py` 425, then 426, ahead of 428"
  - claim: "A session already closed is left alone"
    source: "`binance_adapter.py` 427 into 428"
  - claim: "Entering as a context makes the session and answers the adapter itself"
    source: "`binance_adapter.py` 397, then 398"
  - claim: "Leaving as a context closes it, whatever the reason for leaving"
    source: "`binance_adapter.py` 409"
  - claim: "Registering an account keeps its credentials and makes a health tracker where none stood, under a lock"
    source: "`binance_adapter.py` 444, then 445 into 446"
  - claim: "Unregistering removes the credentials outright, raising where there were none, and drops the tracker tolerantly"
    source: "`binance_adapter.py` 460, then 461 into 462"
---
# What closing the adapter does first

Closing the adapter sets its closed mark before it does anything to the session, and that order is the whole point.

## The order

The closed mark first. Then the session is taken out of the field, and only then closed.

So a task racing to make sure a session exists finds the adapter already marked closed and refuses, rather than building a fresh session the adapter would no longer be tracking. And a task that already held the old session cannot find it in the field to reuse.

A session already closed is left alone.

## As a context

Entering makes the session and answers the adapter itself. Leaving closes it, whatever the reason for leaving — so an error inside the block closes the session as surely as a clean exit does.

## Registering an account

Its credentials are kept, and a health tracker made where none stood, under a lock. The tracker is only created where absent, so re-registering an account keeps whatever its tracker had recorded.

## Unregistering

The credentials are removed outright, raising where there were none. The tracker is dropped tolerantly.

So the two halves disagree about a missing account: the credentials insist it was there, and the tracker does not mind.

## Related

- [How the adapter reckons its headroom](how-the-adapter-reckons-its-headroom.md)
