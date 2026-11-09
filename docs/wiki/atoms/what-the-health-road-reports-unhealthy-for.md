---
row: P131-01
baseline: 49aa659
created: 2026-11-09 10:10 UTC
modified: 2026-11-09 10:10 UTC
evidence:
  - claim: "A list of failures is gathered, with a name added where the host's own stop has been set"
    source: "`launcher.py` 3863, then 3865 into 3866"
  - claim: "A name is added where there is no trading stack, or where it has not started"
    source: "`launcher.py` 3868 into 3869"
  - claim: "A name is added where the loop's thread is absent or no longer alive"
    source: "`launcher.py` 3871 into 3872"
  - claim: "Every account thread that is no longer alive is gathered by name, and one name added carrying all of them"
    source: "`launcher.py` 3874-3876, then 3877 into 3878"
  - claim: "All four are weighed before anything is answered, so the answer names every one that failed"
    source: "`launcher.py` 3880 into 3881-3884"
  - claim: "An empty list answers that all is well"
    source: "`launcher.py` 3885"
  - claim: "Nothing about the caller is weighed, where the figures road beside it demands a loopback address and the operator roads demand three things"
    source: "`launcher.py` 3863, against 3340 into 3341, and 3416 into 3417"
---
# What the health road reports unhealthy for

The health road answers whether the host is fit to keep running, and it weighs four things about the host and nothing at all about the caller.

## The four

Whether the host's own stop has been set. Whether there is a trading stack and whether it has started. Whether the loop's thread is there and still alive. And which of the account threads are no longer alive, gathered by name.

Each adds a name to a list, and all four are weighed before anything is answered — so the answer names every one that failed rather than stopping at the first.

An empty list answers that all is well; any failure answers unhealthy, carrying the names.

## What the account threads tell it

They are checked by whether they are alive, and the dead are named in the answer. Each is a daemon thread, so one that ended on its own account appears here rather than holding the host open.

## The one road that asks nothing of its caller

Nothing about the caller is weighed. The figures road on [the same listener](what-the-one-listener-serves.md) demands a loopback address, and [the operator roads](what-every-operator-road-weighs-first.md) demand three things.

So the road a container polls to decide whether to restart the host is open to anything that can reach the port, and what it gives away is a list of which parts of the host have stopped.

## Related

- [What the one listener serves](what-the-one-listener-serves.md)
- [What every operator road weighs first](what-every-operator-road-weighs-first.md)
- [Starting a host](starting-a-host.md)
