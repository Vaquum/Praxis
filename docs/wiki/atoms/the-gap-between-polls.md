---
row: P11-02
baseline: 49aa659
created: 2026-11-10 07:30 UTC
modified: 2026-11-10 07:30 UTC
evidence:
  - claim: "The gap between polls is a wait on the stop signal bounded by the interval"
    source: "`praxis/infrastructure/book_poller.py` 88-89"
  - claim: "The interval running out carries the loop on to its next turn"
    source: "`praxis/infrastructure/book_poller.py` 90-91"
---
# The gap between polls

The gap a poller leaves between polls is a wait on its stop signal with the interval as a limit, rather than a sleep of the interval.

## What that means for a turn

The waiting ends one of two ways. The signal comes, and the loop's own test sends it no further. Or the limit runs out, and the loop carries on to its next turn.

So the interval is the longest the gap can be, and a gap cut short by the signal is shorter.

## What it means for a stop

A stop is noticed at once. The poller is not sleeping through the interval and so does not have to be woken or waited out: setting the signal ends the wait in hand.

Running a poller on an interval of a twentieth of a second and stopping it part way through a gap returns in a time too small to measure, against a gap of fifty milliseconds.

That is the one place this loop differs in shape from the others, which set a timer for the next turn and cancel it.

## Related

- [What a book poller refuses and answers](what-a-book-poller-refuses-and-answers.md)
- [The stop that waits for its pollers](the-stop-that-waits-for-its-pollers.md)
- [What a loop's stop leaves running](what-a-loops-stop-leaves-running.md)
