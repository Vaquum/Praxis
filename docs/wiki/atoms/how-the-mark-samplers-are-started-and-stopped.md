---
row: P124-01
baseline: 49aa659
created: 2026-11-09 09:46 UTC
modified: 2026-11-09 10:25 UTC
evidence:
  - claim: "Starting does nothing where the loop or the host's record is missing"
    source: "`launcher.py` 3699 into 3700"
  - claim: "The building does nothing where the record is missing, or where samplers already stand"
    source: "`launcher.py` 3717 into 3718"
  - claim: "It reads where the bars are kept from the environment, with a standing folder where none is given, and builds a reader over it"
    source: "`launcher.py` 3720, then 3721"
  - claim: "The cadence and the epoch are each read once, before any sampler is built"
    source: "`launcher.py` 3722, then 3723"
  - claim: "One sampler is built per account, each with a price reader bound to that account"
    source: "`launcher.py` 3731, then 3733-3734, then 3736-3743"
  - claim: "Each is added to a list of its own and started at once"
    source: "`launcher.py` 3744, then 3745"
  - claim: "The whole walk that builds them is wrapped, and a failure part way through stops every sampler already started and raises"
    source: "`launcher.py` 3730, then 3747 into 3748-3751"
  - claim: "The host's own list is reached only past that raise, so a later build starts from an empty set"
    source: "`launcher.py` 3753, against 3747-3751"
  - claim: "Stopping does nothing where the loop is missing or no sampler stands"
    source: "`launcher.py` 3758 into 3759"
  - claim: "It takes the list, hands a stop of every one to the loop, and waits ten seconds for the whole walk"
    source: "`launcher.py` 3761, then 3763-3765, then 3767, then 3770"
  - claim: "The wait is wrapped, and a walk that fails keeps the list standing where one that answers clears it"
    source: "`launcher.py` 3769, then 3771 into 3772, against 3775"
---
# How the mark samplers are started and stopped

A mark sampler writes down what a position is worth at a steady cadence, one per account, and the host starts and stops the whole set together.

## What the start needs

Nothing happens where the loop or the host's own record is missing. The building then does nothing where the record is missing, or where samplers already stand — so starting twice builds one set.

## What the build reads once

Where the bars are kept, taken from the environment with a standing folder where none is given, and a reader built over it. The cadence and the epoch, each read once before any sampler is built. So every sampler in a set shares one cadence, whatever each account asked for.

## One per account

Each gets a price reader bound to its own account, is added to a list of its own, and is started at once rather than after the set is complete.

The whole walk is wrapped, so a failure part way through — which has samplers already running — stops every one of them and raises. The line that would record the set stands past that raise, so a later build starts from an empty set rather than from a half-built one.

## What a stop keeps

Stopping takes the list, hands a stop of every one to the loop, and waits ten seconds for the whole walk rather than for each.

A walk that fails keeps the list standing. Only a walk that answers clears it, so a host that could not stop its samplers still knows which they were.

## Related

- [What the mark sampler is built with](what-the-mark-sampler-is-built-with.md)
- [The stop that waits for its pollers](the-stop-that-waits-for-its-pollers.md)
- [Where the bars are kept](where-the-bars-are-kept.md)
