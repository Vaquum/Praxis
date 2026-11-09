---
row: P134-02
baseline: 49aa659
created: 2026-11-15 11:30 UTC
modified: 2026-11-16 11:30 UTC
evidence:
  - claim: "One pass over the history answers what both the scheme resume and the ladder resume need"
    source: "`execution_manager.py` 1210, then 1214, read back at 1189, and 1190"
  - claim: "A scheme start is kept only where none stands for that command, and a ladder start kept again under a set of its own"
    source: "`execution_manager.py` 1215 into 1216, then 1218 into 1219"
  - claim: "The latest state a scheme reached is kept with the place in the history it arrived at"
    source: "`execution_manager.py` 1221 into 1222-1223"
  - claim: "A failed slice freezes the command, where a freeze for protection marks it twice — frozen, and frozen for protection"
    source: "`execution_manager.py` 1225 into 1226, against 1228 into 1229-1230"
  - claim: "A replan is kept with its place too, and where it says so it lifts the freeze, which lifts only the slice-failure one"
    source: "`execution_manager.py` 1232 into 1233-1234, then 1236 into 1240"
  - claim: "A draining record marks the command draining and keeps the status, state and reason it is to end with"
    source: "`execution_manager.py` 1242 into 1243-1248"
  - claim: "An outcome of a terminal status is kept as the command having ended"
    source: "`execution_manager.py` 1250 into 1251"
  - claim: "A ladder's amend is followed as a little machine: an initiation opens it as cancelling, a plan moves it to placing where an initiation stands, and an unknown state takes its phase off the event"
    source: "`execution_manager.py` 1253 into 1254-1255, or 1257 into 1258, then 1261 into 1262, or 1264, then 1267 into 1268-1270"
  - claim: "A completion builds the new grid from the initiation and the plan kept under that generation, and records nothing at all where no initiation was kept"
    source: "`execution_manager.py` 1272 into 1273-1274, then 1276-1283, then 1285 into 1286-1288"
  - claim: "A completion and an abort each clear the in-flight record"
    source: "`execution_manager.py` 1290, or 1292 into 1293, then 1295"
---
# What one pass gathers for the schemes

One pass over an account's history gathers everything the resuming of a scheme and the resuming of a ladder both need, instead of each walking the record for itself.

## The two kinds of start, kept apart

A scheme start is kept only where none stands for that command, so the first of them wins. A ladder start is kept again under a set of its own.

Keeping them apart is what lets a ladder resume from the first ladder start while a scheme resumes from the first start of any mode.

## What is remembered with its place

The latest state a scheme reached, and any replan, are each kept with the place in the history they arrived at — so the resuming can tell which of the two came later.

## The two freezes

A failed slice freezes the command. A freeze for protection marks it twice: frozen, and frozen for protection. A replan that says so lifts the freeze, and lifts only the slice-failure one.

So a scheme frozen for protection stays frozen through any number of replans, and one frozen for a failed slice does not.

## A draining scheme

Marked draining, with the status, the state and the reason it is to end with all kept.

## The ladder's amend, followed as a machine

An initiation opens it as cancelling. A plan moves it to placing, where an initiation stands. An unknown state takes its phase off the event itself.

A completion builds the new grid from the initiation and the plan kept under that generation — and records nothing at all where no initiation was kept. A completion and an abort each clear the in-flight record.

## Related

- [How a restart reads its record back](how-a-restart-reads-its-record-back.md)
- [What a restart puts back](what-a-restart-puts-back.md)
- [How a ladder's prices are changed](how-a-ladders-prices-are-changed.md)
