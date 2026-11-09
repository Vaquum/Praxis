---
row: P132-01
baseline: 49aa659
created: 2026-11-15 10:30 UTC
modified: 2026-11-15 10:30 UTC
evidence:
  - claim: "The settings, the record or the path to one, the venue, the port, the two folders and whether permissions are enforced are each kept as handed in"
    source: "`launcher.py` 2770, then 2774, then 2776, then 2777, then 2780, then 2781, then 2783, then 2784"
  - claim: "The accounts alone are copied, into a list of the host's own"
    source: "`launcher.py` 2775"
  - claim: "A stop of its own, a cache for the book and a sink for alerts are built there rather than handed in"
    source: "`launcher.py` 2785, then 2793, then 2795"
  - claim: "The sink is built reading the address to post to from the environment, and a posting opens a session of its own under a total deadline and raises on an answer that is not a success"
    source: "`launcher.py` 2795-2798, into 886, then 889"
  - claim: "Whether the host owns the record it writes to is remembered as whether none was handed in"
    source: "`launcher.py` 2779"
---
# What a host keeps as it is built

A host is handed its settings and its surroundings once, and what it does with each of them at that moment decides what can change afterwards.

## Kept as it came

The settings, the record or the path to one, the venue, the port, the two folders, and whether permissions are to be enforced. Each is held as handed in, so a caller holding the same object still holds the host's.

## Copied

The accounts alone. A caller that adds one to its own list afterwards is not adding one to the host's.

## Built rather than handed in

A stop of its own, [a cache for the book](the-kept-book.md), and a sink for alerts. The sink reads the address to post to from the environment, so where to send an alert is settled at this moment and not when one is raised.

A posting opens a session of its own for the one post, under a total deadline, and raises on an answer that is not a success.

## What one of them is remembered as

Whether the host owns the record it writes to is not kept as a thing of its own — it is remembered as whether none was handed in, which is what later decides whether closing the host closes the record.

## Related

- [What a host refuses to be built as](what-a-host-refuses-to-be-built-as.md)
- [Alerts](alerts.md)
- [The kept book](the-kept-book.md)
