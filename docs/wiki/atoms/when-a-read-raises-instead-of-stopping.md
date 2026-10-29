---
row: N8-08
baseline: 49aa659
created: 2026-10-28 18:55 UTC
modified: 2026-10-29 08:56 UTC
evidence:
  - claim: "A payload passing all five is turned into a record by a step nothing wraps, so a failure there raises out of the read rather than returning what came before"
    source: "`nexus/infrastructure/wal.py` 219 with no catch around it, raising at 334 or 344 instead of reaching the return at 220"
  - claim: "A second reader stops the same way on a short header or a payload that runs out, and raises instead on a marker that is present and wrong, on a length past the cap, or on a checksum that does not match; nothing under `nexus/` calls it"
    source: "`nexus/infrastructure/wal.py` 144-147 and 155-159 against 137-139, 149-154 and 160-163, where that wrong marker instead returns at 197-198, with no call to it anywhere under `nexus/`"
---
# When a read raises instead of stopping

A raise out of a read costs the caller the whole file: where the read would have handed back the records it had already taken, it hands back none of them.

## A payload that will not become a record

A payload that has [passed all five checks](what-a-damaged-record-costs.md) is then turned into a record. That step can fail on its own account: on bytes that unpack into something other than a record, or into one missing a field it must carry.

Nothing wraps it. So where it fails the read raises, and the caller is given none of the records that came before — including the ones already taken from earlier in the same file.

## The reader that refuses what the other forgives

The log carries a second way of reading it. On a short head or a payload that runs out it stops quietly, as the other does. On a marker that is present and wrong it raises, where the other reads the file as holding nothing. On a length past the cap or a checksum that fails it raises as well.

No code under the Nexus package calls that second reader.

## Related

- [What a damaged record costs](what-a-damaged-record-costs.md)
- [How a record reaches the log](how-a-record-reaches-the-log.md)

---

Created 2026-10-28 18:55 UTC · Last modified 2026-10-29 08:56 UTC
