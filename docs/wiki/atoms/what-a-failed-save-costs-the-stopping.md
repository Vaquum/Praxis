---
row: N7-12
baseline: 49aa659
created: 2026-10-27 23:30 UTC
modified: 2026-11-13 17:30 UTC
evidence:
  - claim: "The directory is made where needed, and a failure to make it ends the writing for every strategy at once"
    source: "`nexus/startup/shutdown_sequencer.py` 835-836 against 837-839"
  - claim: "A write that fails on the disk is logged and the rest are still tried"
    source: "`nexus/startup/shutdown_sequencer.py` 860-861 over the writing at 854-858"
  - claim: "The failure lands on a temporary file, so the file that strategy had before is left as it was"
    source: "`nexus/startup/shutdown_sequencer.py` 851 and 854-857 before the rename at 858"
  - claim: "A raise of another kind escapes that catch, as writing makes over a blob that is neither bytes nor bytes-like, with the temporary file already opened"
    source: "`nexus/startup/shutdown_sequencer.py` 855 after 854, outside the one kind caught at 860"
  - claim: "A blob that counts as nothing is passed over before any of that, so an empty answer costs the stopping nothing"
    source: "`nexus/startup/shutdown_sequencer.py` 843-844 before 850"
  - claim: "Nothing in the stopping sequence wraps this stage, so such a raise leaves its own checkpoint and its own giving back undone"
    source: "`nexus/startup/shutdown_sequencer.py` 191 before 193 and 196, with no catch around 191"
  - claim: "The raise is caught where the sequence was run, while the host's own stopping gives every account it still holds back on a road of its own, the two set going by one stop and joined for a limited time"
    source: "`praxis/launcher.py` 4030-4035, against 3908-3919 into `praxis/trading.py` 783-785, both set going at `praxis/launcher.py` 2837-2840 and 3999"
  - claim: "The timer that would otherwise write one was stopped before the sequence began, though a turn already under way still writes"
    source: "`praxis/launcher.py` 4006 before 4009, the turn running on at `nexus/infrastructure/snapshot_scheduler.py` 119-123 into 147"
  - claim: "Where anything was written, the directory itself is pushed to the disk too, and a failure at that is logged and passed over"
    source: "`nexus/startup/shutdown_sequencer.py` 841 set at 859, read at 863 into 864-869 against 870-871"
---
# What a failed save costs the stopping

A failure while [saving what the strategies hold](what-a-stopping-host-saves-of-its-strategies.md) costs one strategy's update, or every strategy's, or the rest of the stopping, by which failure it is.

## One strategy's

A write that fails on the disk is logged and the rest are still tried, so one strategy's update is lost and the others land. It fails on a temporary file, so what that strategy saved before is left as it was.

## Every strategy's

A failure to make the directory ends the writing before the first strategy. No update is saved, and the stopping goes on.

## The rest of the stopping

A raise of a kind the catch does not cover escapes the stage — what writing makes over a blob that is neither bytes nor bytes-like, the temporary file already opened for it. Nothing wraps this stage, so that raise carries off [the checkpoint](what-a-checkpoint-holds.md) and [the sequence's own giving back of the account](the-last-record-a-stopping-host-writes.md).

The account is given back even so, on a road of its own: the raise is caught where the sequence was run, while the host's own stopping hands back every account it still holds. One stop sets both going and the host waits only so long for the sequence, so that handing back can come before the raise as easily as after. The checkpoint is what is lost. The timer that would otherwise write one was stopped before the sequence began, though [a turn already under way](what-a-loops-stop-leaves-running.md) still writes.

It takes a value counting as something: one counting as nothing is passed over before the file is opened.

## What is tolerated

Where anything was written, the directory itself is pushed to the disk too. A failure there is logged and passed over, so the renames can be left unflushed.

## Related

- [What a stopping host saves of its strategies](what-a-stopping-host-saves-of-its-strategies.md)
- [The last record a stopping host writes](the-last-record-a-stopping-host-writes.md)

---

Created 2026-10-27 23:30 UTC · Last modified 2026-10-27 23:30 UTC
