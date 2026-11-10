---
row: N8-08
baseline: 49aa659
created: 2026-10-28 18:55 UTC
modified: 2026-11-05 11:10 UTC
evidence:
  - claim: "A payload passing all five is turned into a record by a step nothing wraps, so a failure there raises out of the read rather than returning what came before"
    source: "`nexus/infrastructure/wal.py` 219 with no catch around it, raising at 334 or 344 instead of reaching the return at 220"
  - claim: "That step can fail in six places: the unpacking itself, something other than a record coming back from it, a moment that will not read, a kind the record has no match for, a field missing, and the record's own checks on what it is handed"
    source: "`nexus/infrastructure/wal.py` 331, then 332-334 where what comes back is not a record, or 336-340 where it is, failing at 338 on the moment and at 339 on the kind, the record's own checks standing at `nexus/infrastructure/wal_entry.py` 43-45 and 55-57"
  - claim: "The one catch inside the step takes the missing field alone"
    source: "`nexus/infrastructure/wal.py` 342-344 behind the try at 335"
  - claim: "Both of the log's readers run that step with nothing around it, so any of the six raises out of either read"
    source: "`nexus/infrastructure/wal.py` 164 before the return at 165, and 219 before the return at 220"
  - claim: "A second reader stops the same way on a short header or a payload that runs out, and raises instead on a marker that is present and wrong, on a length past the cap, or on a checksum that does not match; nothing under `nexus/` calls it"
    source: "`nexus/infrastructure/wal.py` 144-147 and 155-159 against 137-139, 149-154 and 160-163, where that wrong marker instead returns at 197-198, with no call to it anywhere under `nexus/`"
---
# When a read raises instead of stopping

A raise out of a read costs the caller the whole file: where the read would have handed back the records it had already taken, it hands back none of them.

## A payload that will not become a record

A payload that has [passed all five checks](what-a-damaged-record-costs.md) is then turned into a record. That step can fail in six places: the unpacking itself; something other than a record coming back from it; a moment that will not read; a kind the record has no match for; a field missing; and the record's own checks on what it is handed.

One catch sits inside the step, and it takes the missing field alone. The other five raise as they are.

Nothing wraps the step from outside, and both of the log's readers run it with nothing around it. So where it fails the read raises, and the caller is given none of the records that came before — including the ones already taken from earlier in the same file.

## The reader that refuses what the other forgives

The log carries a second way of reading it. On a short head or a payload that runs out it stops quietly, as the other does. On a marker that is present and wrong it raises, where the other reads the file as holding nothing. On a length past the cap or a checksum that fails it raises as well.

No code under the Nexus package calls that second reader.

## Related

- [What a damaged record costs](what-a-damaged-record-costs.md)
- [How a record reaches the log](how-a-record-reaches-the-log.md)

---

Created 2026-10-28 18:55 UTC · Last modified 2026-11-05 11:10 UTC
