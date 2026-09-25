---
row: P2-23
baseline: 49aa659
created: 2026-09-24 20:16 UTC
modified: 2026-09-25 18:14 UTC
evidence:
  - claim: "The clock runs from the time supplied on the command, not from the accept written later"
    source: "`execution_manager.py` 2925 reading the time stored at 3476, the accept taking its own clock at 3517"
  - claim: "Work fed out or laddered, dequeued past that time, is ended before it starts"
    source: "either `execution_manager.py` 3995-3996 or 4004-4005, into 4123-4129"
  - claim: "Only work sent in one go is measured after its send, a linked pair included"
    source: "`execution_manager.py` 4008-4009, the pair cancelled by its own call at 4419-4424"
  - claim: "It is measured only where the status just worked out is pending or partial"
    source: "`execution_manager.py` 4411-4414"
  - claim: "A quote-sized order is called filled on the venue saying so with something filled; a quantity-sized one on its fills covering the amount"
    source: "either `execution_manager.py` 4395-4396 or 4403-4404"
  - claim: "Every status, a full fill included, is reported by the same call at the end"
    source: "`execution_manager.py` 4446-4448"
  - claim: "The moment used is taken when the send returned, or when a chased send was adopted"
    source: "stored at either `execution_manager.py` 4281 or 4291, compared at 4414"
  - claim: "A bracket and a hidden-size order are measured against neither clock"
    source: "dispatched by either `execution_manager.py` 4000 or 4002, the one sending at 4521 and the other returning at 5396, neither reading a clock"
  - claim: "A run or a ladder that starts gets a fresh clock, opened from the moment recorded at its start"
    source: "either `execution_manager.py` 5784-5787 from the time taken at 5760, or 6128-6131 from 6107"
  - claim: "The same pass begins winding either of them up against that clock"
    source: "`execution_manager.py` 5816-5824, which skips one already draining or mid-change at 5817-5821"
  - claim: "Winding up cancels children and leaves the run on the books until they settle"
    source: "`execution_manager.py` 8375-8383, held open at 6355-6356 while a child remains"
  - claim: "Protection whose state the venue could not settle waits on a clock of its own"
    source: "`execution_manager.py` 7511-7512, reached only where the query at 7378-7379 failed and was recorded at 7380-7381, tested at 7394-7396"
---
# Deadlines

A **deadline** is a time by which work is expected to be done: the time supplied on the work, plus the timeout it carries. Praxis measures against it at particular moments, and which moments depends on the kind of work.

## Work that never started

Work meant to be [fed out or laddered](work-already-under-way.md) is measured when [the worker](how-waiting-work-is-drained.md) takes it off the queue, and past the time by then is ended there, reported expired with nothing sent.

A [bracket](how-an-order-is-placed.md) and a hidden-size order skip this check.

## Work that was sent

Only work sent in one go is measured after its send; a linked pair counts. Even then the clock is read only where the status just worked out is pending or partial. Every status is reported by the same call regardless.

The moment used is taken when the send returned, or when [a chased send](when-a-send-is-unclear.md) was adopted. Past the time by then, the order is marked expired and [a cancel is attempted](the-expiry-cancel.md).

Short of the time at that moment, the order is reported as it stands and never measured again — a resting order whose deadline arrives an hour later is untouched.

## A second clock

Work being fed out, and a ladder, get a fresh clock when they start, so one that waited a long time to begin does not inherit the wait. Past that clock a [run](work-already-under-way.md) only *begins* winding up: its children are asked to cancel, and it stays on the books until they settle. One already draining, or mid-change, is skipped entirely.

## Related

- [The expiry cancel](the-expiry-cancel.md)
- [Work already under way](work-already-under-way.md)
- [Order placement](how-an-order-is-placed.md)
