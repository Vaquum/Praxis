---
row: S-04
baseline: 49aa659
created: 2026-10-15 08:40 UTC
modified: 2026-10-15 20:50 UTC
evidence:
  - claim: "The host waits on the stop flag, which a signal sets and an account's own failure sets too"
    source: "`launcher.py` 2837, set at 2844 and 4040, the handlers installed at 2824-2825"
  - claim: "Trading marks itself stopping first, and from then every way in is refused"
    source: "`trading.py` 655 before 1878-1880, 1904-1906 and 1913-1915"
  - claim: "The squaring loop is called off before any work is abandoned"
    source: "`trading.py` 657-661 before 665"
  - claim: "Every command in flight is put onto the priority line, and the second pass begins without waiting for the worker to take them"
    source: "`trading.py` 665-670 into `execution_manager.py` 3027, before `trading.py` 700"
  - claim: "An order belonging to a command still in flight is passed over by that second pass"
    source: "`trading.py` 701-702"
  - claim: "An order put up to close a position is passed over by name"
    source: "`trading.py` 704 into 721"
---
# Stopping a host with work in flight

The route a host takes when it is told to stop while requests are part-way through and orders are resting at the venue. Each sentence hands off to the article owning the behaviour it names, and the order they happen in is proved below rather than borrowed.

**Starts from** a running host whose stop flag has been set.

**Ends** with the host shutting down, which can be with work still open at the venue.

## What sets it off

1. A signal sets the stop flag where the host was started on the main thread, and so does an exception escaping an account's own thread — [Stopping a host](../atoms/stopping-a-host.md).

2. Once the trading it runs is told to stop, it refuses new requests, cancellations and changes on the call — [What the host refuses first](../atoms/what-the-host-refuses-first.md).

## The first pass — abandon what is in flight

3. The loop that squares the books against the venue is called off first — [What becomes of work still open](../atoms/what-becomes-of-work-still-open.md).

4. Every command still in flight is then sent an abandonment marked as a shutdown, onto the line the worker takes priority work from — [What becomes of work still open](../atoms/what-becomes-of-work-still-open.md).

5. Each of those takes the same three arms a cancellation does, whenever the worker picks it up — [Where an abandonment lands](../atoms/where-an-abandonment-lands.md). Stopping does not wait for that: it goes on to its own pass while they sit on the line — [What stopping leaves undone](../atoms/what-stopping-leaves-undone.md).

6. An abandonment refused on the way in — no worker left to drain it, among other grounds — has its command struck from the skip list, so the next pass picks its orders up instead — [What becomes of work still open](../atoms/what-becomes-of-work-still-open.md).

## The second pass — cancel what is resting

7. The orders still resting are then cancelled where they stand, a protective pair through the call meant for pairs — [What becomes of work still open](../atoms/what-becomes-of-work-still-open.md), [Protection](../atoms/protection.md).

8. An order belonging to a command still in flight is passed over, since the abandonment covers it — [What becomes of work still open](../atoms/what-becomes-of-work-still-open.md).

9. An order put up to close a position is passed over deliberately, known by the names this account recorded when it posted one — cancelling it would hand back a position this host can no longer watch — [What becomes of work still open](../atoms/what-becomes-of-work-still-open.md).

## What it carries on through

10. A cancel the venue refuses, a drain that runs out of time, and a close that fails are each logged and the next step taken up, so stopping can finish with things still open — [What stopping leaves undone](../atoms/what-stopping-leaves-undone.md).

11. Being called off is not one of those: it is passed straight on, and the step after it is left undone entirely — [What stopping leaves undone](../atoms/what-stopping-leaves-undone.md).

12. The worker itself stops taking work, and what the account is left as turns on which way it stopped — [How a worker stops](../atoms/how-a-worker-stops.md). What the rest of the host does from here, and what it is left with, is its own subject — [Stopping a host](../atoms/stopping-a-host.md).

## Where this route is not taken

- An account poisoned while running refuses its queued work without the host stopping at all — [When an account is reconciling or poisoned](../atoms/when-an-account-is-reconciling-or-poisoned.md).
- A caller cancelling one request takes the ordinary route instead — [Cancellation](../atoms/how-a-trade-is-cancelled.md).

---

Created 2026-10-15 08:40 UTC · Last modified 2026-10-15 20:50 UTC
