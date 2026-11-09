---
row: P90-01
baseline: 49aa659
created: 2026-11-13 22:30 UTC
modified: 2026-11-13 22:30 UTC
evidence:
  - claim: "A server refuses an empty host, and a port outside the range a port can take"
    source: "`server.py` 947 into 948, then 950 into 951"
  - claim: "The application is built as the server is built, so every road into it exists before any start"
    source: "`server.py` 955, ahead of 971"
  - claim: "A server counts as running where a site exists, and that field is set only after a start has succeeded"
    source: "`server.py` 967, the field set at 998"
  - claim: "Starting while already running raises before anything is made"
    source: "`server.py` 971 into 972"
  - claim: "A runner is made and set up, then a site for the host and port"
    source: "`server.py` 980-981, then 983"
  - claim: "The site's start stands inside a guard that names every failure there can be, which cleans the runner up and raises on"
    source: "`server.py` 985-986 into 987, then 994, then 995"
  - claim: "The runner and the site are recorded only once that start has returned"
    source: "`server.py` 997, and 998"
  - claim: "Stopping weighs the site and the runner one at a time, stopping or cleaning each and clearing it where it is there"
    source: "`server.py` 1002 into 1003-1004, then 1006 into 1007-1008"
---
# What binsim's server holds and when

A server is built with its application already made, and holds a runner and a site only while it is up.

## What the building refuses

An empty host, and a port outside the range a port can take. Nothing else is asked.

The application is built as the server is built, so every road into it exists before any start — a server that has never been started still has an application to hand out.

## What running means

A site exists. That field is set only after a start has succeeded, so a failed start leaves the server reading as stopped and holding neither a runner nor a site.

Starting while already running raises before anything is made.

## The start

A runner is made and set up, then a site for the host and port. The site's start stands inside a guard that names every failure there can be, a cancelling of the task among them, which cleans the runner up and raises on.

The runner and the site are recorded only once that start has returned. So the server either holds both or holds neither, and no failure leaves half of it behind.

## The stop

The site and the runner are weighed one at a time, each stopped or cleaned and cleared where it is there. So a server holding only one of the two can still be stopped, and stopping one that holds neither does nothing at all.

## Related

- [What binsim's read endpoints answer](what-binsims-read-endpoints-answer.md)
