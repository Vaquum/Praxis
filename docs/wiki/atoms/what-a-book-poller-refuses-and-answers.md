---
row: P11-01
baseline: 49aa659
created: 2026-11-08 13:58 UTC
modified: 2026-11-08 13:58 UTC
evidence:
  - claim: "A poller refuses an empty symbol"
    source: "`praxis/infrastructure/book_poller.py` 31-32"
  - claim: "It refuses an interval at or below nought, by comparison and not by type"
    source: "`praxis/infrastructure/book_poller.py` 34-35, which compares and asks no type"
  - claim: "It answers that it is running where its task exists and has not finished"
    source: "`praxis/infrastructure/book_poller.py` 46-47"
  - claim: "Starting one that is already running is refused, by reading that answer"
    source: "`praxis/infrastructure/book_poller.py` 52-53"
  - claim: "Starting clears the stop signal before it makes a task named for the symbol"
    source: "`praxis/infrastructure/book_poller.py` 55 into 56-58"
---
# What a book poller refuses and answers

A poller keeping [the order book](the-order-book.md) fresh refuses two things as it is made and answers one question about itself afterwards.

## The two refusals

An empty symbol. An interval at or below nought.

Both are comparisons, and neither asks the figure or the text for its type. An interval that is not a number passes, because the comparison answers false for it, and the poller then waits on arithmetic with it.

## The answer

It is running where its task exists and has not finished. So a poller that was never started answers no, and one whose task has ended answers no as well, without anything being told that it ended.

## What reads that answer

Starting refuses where the answer is yes, so a poller cannot be started twice over.

Starting also clears the stop signal before it makes the task. That is what lets a stopped poller be started again: the signal left standing by the last stop would otherwise end the new loop on its first turn.

The task is named for the symbol, so one poller's task can be told from another's.

## Related

- [The gap between polls](the-gap-between-polls.md)
- [The stop that waits for its pollers](the-stop-that-waits-for-its-pollers.md)
- [The kept book](the-kept-book.md)
