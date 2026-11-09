---
row: P129-02
baseline: 49aa659
created: 2026-11-15 09:00 UTC
modified: 2026-11-15 10:30 UTC
evidence:
  - claim: "A terminal outcome drops the command's registration under the registry's lock"
    source: "`launcher.py` 4380, then 4381 into 4382"
  - claim: "Where that command was an entry carrying a trade name, the position is looked up under the positions lock"
    source: "`launcher.py` 4383, then 4384-4387, then 4388, then 4389"
  - claim: "It is deleted only where nothing is left of it"
    source: "`launcher.py` 4390 into 4391"
  - claim: "That deletion is remembered, and is what sends the bracket's protective registration to be dropped"
    source: "`launcher.py` 4392, then 4393 into 4394-4398"
  - claim: "Whether the command still stands marked as unsaved is read under the registry's lock again, after all of that"
    source: "`launcher.py` 4400, then 4401"
---
# What a terminal outcome removes

A terminal outcome is the last word on a command, and working it through takes three things out of the host's own records.

## The registration

Dropped under the registry's lock, for every terminal outcome whatever it says. So a command that ended in a refusal and one that filled whole are forgotten here alike.

## The position

Only where the command was an entry carrying a [trade name](what-a-trade-is.md). The position is looked up under the positions lock and deleted only where nothing is left of it — so an entry that filled and was then sold out entirely goes, and one still holding something stays.

## The bracket's protection

The deletion is remembered, and that memory is the only thing that sends [the bracket's protective registration](what-a-brackets-protective-exit-is-registered-as.md) to be dropped. An entry that left a position behind keeps its protective record, which is what the protection will fill against.

So the one record is kept exactly while there is a position for it to protect.

## What is read afterwards

Whether the command still stands marked as unsaved, under the registry's lock again, after all three removals. The lock is therefore taken twice in one pass, and what the second read finds is whatever was marked before the pass began.

## Related

- [What a bracket's protective exit is registered as](what-a-brackets-protective-exit-is-registered-as.md)
- [How a command's unwritten mark is let go](how-a-commands-unwritten-mark-is-let-go.md)
- [The watch over handovers that timed out](the-watch-over-handovers-that-timed-out.md)
