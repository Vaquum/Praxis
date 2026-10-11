---
row: P4-01
baseline: 49aa659
created: 2026-10-01 10:12 UTC
modified: 2026-10-11 19:29 UTC
evidence:
  - claim: "A host is one process running Praxis and Nexus together"
    source: "`launcher.py` 2847-2853 for the loop thread and 3892-3902 for the account threads"
  - claim: "Seven calls are made in a fixed order, and the host then waits on the stop flag"
    source: "`launcher.py` 2827-2837"
  - claim: "The handlers for the stop signals are set before them, only where the start happens on the main thread"
    source: "`launcher.py` 2823-2825"
  - claim: "The key check does nothing unless it is turned on"
    source: "`launcher.py` 3062-3063"
  - claim: "The endpoint does nothing unless a port was given"
    source: "`launcher.py` 3267-3268"
  - claim: "The book pollers do nothing unless a venue was handed in, which the ordinary start does not do"
    source: "`launcher.py` 3799-3800 against the build at 4984-4991"
  - claim: "The record's file is made if missing and the record opened on it, unless one was handed in"
    source: "`launcher.py` 3127-3130, reached from 2950-2955"
  - claim: "One queue is made for each host run and kept under its account, and the routes back are set"
    source: "`launcher.py` 2966-2968 and 2994-3040"
  - claim: "The caller waits thirty seconds for trading to start"
    source: "`launcher.py` 3042-3043"
---
# Starting a host

A **host** is one process running Praxis and Nexus together: a loop on a thread of its own, and a thread for each [account](what-an-account-is.md). This is what starting one does once the settings have been read; the reading happens before, and is a subject of its own.

## The order

Seven calls, in order: the loop thread, trading, the key check, a thread for each account, the endpoint a watcher polls, the [mark samplers](the-mark-sampler.md), the book pollers. Handlers for the stop signals are set before all seven, and only where the start happens on the main thread. After the seventh the host waits on the stop flag.

## Three that can do nothing

The key check returns at once unless it is turned on. The endpoint returns unless a port was given. The book pollers return unless a venue was handed in. The ordinary start hands one in nowhere, so on that path the pollers return every time.

## What trading does

It makes [the record's](the-event-spine.md) file if the file is missing and opens the record on it, unless a record was handed in. It makes one queue for each host run, kept under that run's account, and sets the routes back along which an outcome will travel. Then it starts, and the caller waits thirty seconds for that.

## Related

- [What a failure at startup does](what-a-failure-at-startup-does.md)
- [What an account is](what-an-account-is.md)
