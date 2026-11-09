---
row: P118-02
baseline: 49aa659
created: 2026-11-15 03:30 UTC
modified: 2026-11-15 03:30 UTC
evidence:
  - claim: "The watch is built with no timer yet, a flag reading not running, and a lock of its own apart from the one over the registry it scans"
    source: "`launcher.py` 2252, then 2253, then 2254"
  - claim: "Whether it is running is answered from that flag"
    source: "`launcher.py` 2260"
  - claim: "Starting takes its own lock, answers at once where the flag already reads running, and otherwise sets the flag and schedules a scan"
    source: "`launcher.py` 2265, then 2266 into 2267, or 2269, then 2270"
  - claim: "Scheduling reads the flag again and schedules nothing where it reads not running"
    source: "`launcher.py` 2313 into 2314"
  - claim: "The timer it sets is marked a daemon before it is started"
    source: "`launcher.py` 2316, then 2317, then 2318"
  - claim: "A tick reads the flag under that lock and lets the lock go before the scan runs"
    source: "`launcher.py` 2321, then 2322 into 2323, or 2325-2326"
  - claim: "Any failure out of a scan is caught and reported, and the next scan scheduled all the same, under that lock again"
    source: "`launcher.py` 2327-2328, then 2330 into 2331"
  - claim: "A scan takes the moment once and weighs every record's age against that one moment"
    source: "`launcher.py` 2284, then 2286-2293"
  - claim: "The gathering is done under the registry's own lock, and the longest wait worked out after that lock is let go"
    source: "`launcher.py` 2286-2293, then 2298"
---
# How the watch keeps itself going

[The watch over handovers that timed out](the-watch-over-handovers-that-timed-out.md) runs on a timer it sets for itself after every scan, and a flag decides whether it sets another.

## The two locks

One is the lock over the registry of commands, shared with whatever writes to it. The other is the watch's own, and it guards nothing but the flag and the timer.

Starting takes its own lock, answers at once where the flag already reads running, and otherwise sets the flag and schedules a scan. Whether the watch is running is answered from that flag.

## Where the flag is read

Twice in every round: as a tick begins, and again as the next scan is scheduled. A start reads it as well, which is how a second start does nothing.

So a stop during a scan cannot cut the scan short — the tick lets the lock go before the scan runs — and is caught instead at the scheduling, which sets no further timer.

## What a failure costs

Nothing. A failure out of a scan is caught and reported, and the next scan is scheduled all the same. One bad pass costs one pass.

## The timer

Marked a daemon before it is started, so a host on its way out leaves a pending scan where it stands rather than waiting for it.

## What a scan reads

The moment once, with every record's age weighed against that one moment, so the records a pass gathers are all judged against the same instant. The gathering is done under the registry's own lock, and the longest wait is worked out after that lock is let go.

## Related

- [The watch over handovers that timed out](the-watch-over-handovers-that-timed-out.md)
- [What a loop's stop leaves running](what-a-loops-stop-leaves-running.md)
