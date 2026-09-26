---
row: P2-17
baseline: 49aa659
created: 2026-09-26 08:12 UTC
modified: 2026-09-26 17:41 UTC
evidence:
  - claim: "Every event is kept with its epoch, time, kind and contents"
    source: "`event_spine.py` 123-131"
  - claim: "Rows go in as they are written, with no sorting or checking of the times"
    source: "`event_spine.py` 1165-1172, the order coming from the key at 124"
  - claim: "A kind the record does not know is refused rather than kept"
    source: "`event_spine.py` 1158-1161"
  - claim: "A fill is offered here before it is projected"
    source: "`execution_manager.py` 4328-4330"
  - claim: "A send writes down the intention before the venue is asked"
    source: "`execution_manager.py` 4264-4265, ahead of the call at 4268-4272"
  - claim: "An answer that could be read is written down after"
    source: "`execution_manager.py` 4301-4308"
  - claim: "A failure of a kind looked for is written down instead"
    source: "reached at `execution_manager.py` 4296-4299, delegated at 5420-5422, built and appended at 5457-5465"
  - claim: "A reply malformed past what is looked for escapes both and leaves only a line in the log"
    source: "raised at `binance_adapter.py` 940, caught by none of the alternatives at `execution_manager.py` 4282, 4292 or 4296, logged at 4012-4019"
  - claim: "One lock serves the writers sharing one spine object"
    source: "`event_spine.py` 456, taken at 947-948"
  - claim: "It is held through the writing, the sealing and the commit"
    source: "`event_spine.py` 1125-1126 inside the lock taken at 947-948, the sealing at 1165-1176"
---
# The event spine

The **event spine** is where Praxis writes down what happens: one row for each event, carrying the epoch it belongs to, its time, what kind of thing it was, and its contents.

Rows are kept in the order they were written. That is not always the order things happened — the times are stored but never sorted on or checked, so a fill reconciled from the venue long afterwards goes in at the end, behind events that came after it.

## What is refused

An event of a kind the record does not know is refused outright rather than written down. Nothing unrecognised gets in.

A [repeated fill](where-duplicates-stop.md) is refused too, and that refusal is ordinary rather than a failure.

## What is written before what

A [fill](what-a-fill-is.md) is written down before it is acted on, and only an accepted one is [passed to the projections](what-a-fill-changes.md).

Sending an order is written down around the act. The intention to send goes in before the venue is asked. What became of it goes in after: the venue's answer where that could be read, or a note of failure where the failure was one of the kinds looked for.

A reply malformed past those kinds escapes both, and only a line in the log marks it. The intention stands in the record with nothing beside it, which is what leaves [such a send](a-reply-that-cannot-be-read.md) readable afterwards as one attempted and unaccounted for.

## One writer at a time

A lock is held from reading the last row through writing, [sealing](the-chain.md) and committing the new one, so writers sharing one spine object cannot fork the chain between them.

The lock belongs to that object. Two spine objects, or two processes, opened on the same file are not held apart by it.

## Related

- [The chain](the-chain.md)
- [Where duplicates stop](where-duplicates-stop.md)
