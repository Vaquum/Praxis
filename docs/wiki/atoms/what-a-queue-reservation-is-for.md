---
row: P149-01
baseline: 49aa659
created: 2026-11-09 11:36 UTC
modified: 2026-11-09 11:36 UTC
evidence:
  - claim: "The queue is weighed as what it already holds plus the reservations standing against it, and a command arriving at the cap is refused"
    source: "`execution_manager.py` 3497-3500, then 3507-3511"
  - claim: "Past that a reservation is taken, and given back whatever happens afterwards"
    source: "`execution_manager.py` 3513, then 3562 into 3563"
  - claim: "The acceptance is recorded while the reservation stands, and a failure writing it undoes both the acceptance and any abort noted against the command, then passes the failure on"
    source: "`execution_manager.py` 3524-3525, then 3526 into 3527-3529"
  - claim: "An account that fail-stopped or failed its startup while that record was being written has the command ended as refused, and the name answered all the same"
    source: "`execution_manager.py` 3531 into 3535-3544, then 3547"
  - claim: "Only then is the command put on the queue, and a queue that refuses it there raises the same full-queue failure"
    source: "`execution_manager.py` 3549-3550, then 3551 into 3561"
  - claim: "The command is installed and given its trade only once the reservation has been given back"
    source: "`execution_manager.py` 3565, then 3566, past 3563"
---
# What a queue reservation is for

A command's place in an account's queue is held before the command is put there, by a count the queue's own length is weighed against.

## What is weighed

What the queue already holds, plus the reservations standing against it. A command arriving when that sum is at the cap is refused outright.

So two commands admitted at once cannot both be told there is room: the first takes a reservation, and the second sees it.

## When the reservation is given back

Whatever happens afterwards. The record of the acceptance is written while it stands, and the command is only installed and given its trade once it has been given back.

## What the record's failure undoes

A failure writing the acceptance undoes both the acceptance and any abort noted against the command, then passes the failure on. So a command whose acceptance failed to record leaves nothing behind.

## The two refusals after the reservation

An account that fail-stopped or failed its startup while that record was being written has its command ended as refused — and the name is answered all the same, so a caller gets a name for a command that was never queued.

A queue that refuses the command at the moment of putting raises the same full-queue failure the first test raises. The reservation is why that second refusal is rare rather than impossible.

## Related

- [How an order is placed](how-an-order-is-placed.md)
- [How waiting work is drained](how-waiting-work-is-drained.md)
- [The two checks around an append](the-two-checks-around-an-append.md)
