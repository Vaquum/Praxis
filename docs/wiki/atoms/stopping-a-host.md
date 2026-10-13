---
row: P4-02
baseline: 49aa659
created: 2026-10-01 17:53 UTC
modified: 2026-10-04 11:43 UTC
evidence:
  - claim: "A host stops when the stop flag is set, which a signal does and an exception escaping an account's thread does"
    source: "`launcher.py` 2844 and 4034-4040, waited on at 2837"
  - claim: "The handler setting it on a signal is installed only where the start happened on the main thread"
    source: "`launcher.py` 2823-2825"
  - claim: "The samplers and the pollers are stopped first"
    source: "`launcher.py` 3905-3906"
  - claim: "Each account's thread is then waited on for up to thirty seconds"
    source: "`launcher.py` 3908-3909"
  - claim: "One still running past that is logged as a warning and the next is taken up"
    source: "`launcher.py` 3911-3915"
  - claim: "Such a thread is a background one, so a process ending does not wait for it"
    source: "`launcher.py` 3898"
  - claim: "Trading is stopped next, waited on for thirty seconds"
    source: "`launcher.py` 3917-3919"
  - claim: "A failure stopping trading, or closing the connection, carries out and the steps after it are skipped"
    source: "`launcher.py` 3917-3919 and 3921-3927, with no handler around either"
  - claim: "The record's connection is closed only where this host opened it, meaning none was handed in"
    source: "`launcher.py` 3921-3927, the test set at 2779"
  - claim: "The endpoint is stopped after that"
    source: "`launcher.py` 3929"
  - claim: "The loop is asked to stop, its thread waited on for five seconds, and the loop closed"
    source: "`launcher.py` 3931-3938"
---
# Stopping a host

A [host](starting-a-host.md) stops when its stop flag is set. A signal sets it, where the start happened on the main thread; so does an exception escaping an [account's](what-an-account-is.md) thread, from building it through to shutting it down.

## The order

The [mark samplers](the-mark-sampler.md) and the book pollers are stopped. Each account's thread is then waited on, for up to thirty seconds each. One still running past that is logged as a warning and the next is taken up; it may yet finish on its own, and a process ending does not wait for it.

Trading is stopped next, waited on for thirty seconds. This is where [work still open](what-becomes-of-work-still-open.md) is dealt with.

The connection to [the record](the-event-spine.md) is closed, but only where this host opened it — which means only where none was handed in. Then the endpoint a watcher polls. Then the loop: it is asked to stop, its thread waited on for five seconds, and the loop closed.

## Each step rests on the one before

The thirty seconds given to trading bounds how long the host waits. The stopping itself goes on running past that.

Two of those steps catch nothing. A stop that fails, or outlasts its thirty seconds, carries straight out, and so does a failure closing the connection — leaving the steps after it undone.

## Related

- [What becomes of work still open](what-becomes-of-work-still-open.md)
- [Starting a host](starting-a-host.md)
