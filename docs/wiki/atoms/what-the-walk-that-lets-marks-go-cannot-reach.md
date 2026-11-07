---
row: P6-01
baseline: 49aa659
created: 2026-11-06 15:07 UTC
modified: 2026-11-07 00:35 UTC
evidence:
  - claim: "A command the copy does not hold has no test run for it at all"
    source: "`praxis/launcher.py` 4459-4460 over the copy taken at 4427, the test at 4461 run for that copy's keys alone"
  - claim: "The lock the copy is taken under is given up before the write runs"
    source: "`praxis/launcher.py` 4426-4427 ending before 4439"
  - claim: "A mark is set only once the accounting that earns it has returned, under that same lock"
    source: "`praxis/launcher.py` 2919 before 2938-2943, the lock taken at 2939 and the earlier block that took it at 2895 having ended at 2900, that lock being the object 4351 hands the wiring and 4426 takes again"
  - claim: "It is set before its own outcome is queued"
    source: "`praxis/launcher.py` 2990 before 2992, the write reached from the queue at 4439"
  - claim: "It is set holding neither of the locks the write's own guard takes"
    source: "`praxis/launcher.py` 2938-2943 reached after 2919 has returned, against `nexus/infrastructure/state_store.py` 220-221"
  - claim: "The one deletion the mapping ever takes is the walk's own"
    source: "`praxis/launcher.py` 4462, with no other deletion from it anywhere under `praxis/`"
---
# What the walk that lets marks go cannot reach

[The walk that lets marks go](how-a-commands-unwritten-mark-is-let-go.md) reads a copy taken before the write, and a command first marked after that copy is one it has no key for.

## The keys it has

A command the copy does not hold has no test run for it at all, so that write leaves its mark standing. What the walk does with the keys it does hold is that article's subject.

## Why a mark can fall outside a copy

A mark goes on once the accounting that earns it has returned, and before its own outcome is queued. What is unordered is one command's mark against another command's write: the setting and the copying take the same lock, each in an acquisition of its own.

## Where it waits

The one deletion the mapping ever takes is that walk's own. A mark no walk has reached therefore stays where it is.

## Related

- [How a command's unwritten mark is let go](how-a-commands-unwritten-mark-is-let-go.md)
- [What the money's lock is doing when a result is written](what-the-moneys-lock-is-doing-when-a-result-is-written.md)
- [Which of a host's changes reach the log](which-of-a-hosts-changes-reach-the-log.md)
