---
row: P64-04
baseline: 49aa659
created: 2026-11-08 19:39 UTC
modified: 2026-11-08 19:39 UTC
evidence:
  - claim: "The payload is built in one go and the writing of it handed to a thread, so the loop is not held while bytes go to disk"
    source: "`ledger.py` 624-631, then 633-635"
  - claim: "The waiting is shielded, so a interruption reaching the waiter leaves the writing to run on"
    source: "`ledger.py` 638-640"
  - claim: "A interruption is noted, the task's own count of interruptions is wound back, and the waiting is entered again until the writing is done"
    source: "`ledger.py` 641-647, the loop at 638"
  - claim: "A failure of the writing comes back out of the shielded waiting, and nothing here catches that kind, so it reaches the caller"
    source: "`ledger.py` 640, the catch beside it naming interruption alone at 641"
  - claim: "The logging is reached only where the waiting ended without raising, which is where a interruption had been handled and the writing failed in the same breath"
    source: "`ledger.py` 638 leaving the loop on a writing already done, into 649-656"
  - claim: "In that one case the interruption is raised and the failure goes no further than the log"
    source: "`ledger.py` 658-659, with the failure only logged at 653-656"
---
# What an interrupted save does

A save of [binsim's ledger](binsims-ledger.md) can be interrupted where the work around it is told to stop. Saving builds the whole payload first and hands the writing of it to a thread, so the loop keeps running while bytes go to disk.

## A interruption does not abandon the write

The waiting is shielded. A interruption reaching the waiter leaves the writing to run on, and the waiting is entered again until it is done.

Each interruption is noted, and the task's own count of interruptions is wound back so the task is not left marked as cancelling while it waits.

So a save caught by a interruption finishes writing, and only then is the interruption raised.

## An ordinary failure reaches the caller

A failure of the writing comes back out of the shielded waiting. The catch beside it names interruption alone, so a failure of any other kind passes straight through to whoever asked for the save.

## The one failure that is swallowed

The logging further down is reached only where the waiting ended without raising — which happens where a interruption had just been handled and the writing failed in the same breath, leaving nothing to await.

There the failure is logged and the interruption raised in its place. A caller sees a cancelled save and learns from the log alone that the save also failed.

That is the case the log's wording names, and it is the only one it is written for.

## Related

- [Binsim's ledger](binsims-ledger.md)
- [How the snapshot is written and read back](how-the-snapshot-is-written-and-read-back.md)
- [What a restart of the simulated venue loses](what-a-restart-of-the-simulated-venue-loses.md)
