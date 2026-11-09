---
row: P90-02
baseline: 49aa659
created: 2026-11-09 07:12 UTC
modified: 2026-11-09 07:12 UTC
evidence:
  - claim: "Building the application refuses a staleness span at or below nought before anything is made"
    source: "`server.py` 180 into 181-183, ahead of 185"
  - claim: "The book, the ledger, the poller and that span are each put on the application under a key of their own"
    source: "`server.py` 186, and 187, and 188, and 189"
  - claim: "A counter of socket subscriptions is made there too, so every connection shares the one"
    source: "`server.py` 190"
  - claim: "Eleven roads are added at once, ten under the method that asks and one under the method that submits"
    source: "`server.py` 192-204"
  - claim: "Two roads share the same path and differ only by method, one answering and one submitting"
    source: "`server.py` 198, against 201"
  - claim: "The application is then handed back, with nothing started"
    source: "`server.py` 206"
  - claim: "The counter of identifiers hands out the figure standing and raises it by one, so no two calls get the same"
    source: "`server.py` 61, then 62, then 64"
---
# What the application is handed and what it serves

The application is built once, handed everything it will need, and handed back without anything started.

## What the building refuses

A staleness span at or below nought, weighed before anything is made.

## The pieces it carries

The book, the ledger, the poller and that span are each put on the application under a key of their own. A counter of socket subscriptions is made there too, so every connection that arrives shares the one counter.

Each handler therefore reaches what it needs through the application rather than through anything it closes over.

## The roads

Eleven are added at once: ten under the method that asks, and one under the method that submits. Two of the eleven upgrade to a socket rather than answering outright.

Two share the same path and differ only by method — one answering about an order, one submitting one.

So a caller using the wrong method on that path reaches the other handler rather than a refusal, and what comes back is shaped by which method was used.

## The counter of identifiers

It hands out the figure standing and raises it by one, so no two calls get the same figure. Nothing guards it, so the figures are unique only while one caller asks at a time.

## Related

- [What binsim's server holds and when](what-binsims-server-holds-and-when.md)
- [What binsim's read endpoints answer](what-binsims-read-endpoints-answer.md)
