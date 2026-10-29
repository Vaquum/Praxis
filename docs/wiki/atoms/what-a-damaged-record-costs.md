---
row: N8-02
baseline: 49aa659
created: 2026-10-28 18:45 UTC
modified: 2026-10-28 18:45 UTC
evidence:
  - claim: "Reading stops at the first damaged record and keeps what came before it, by a short header, a length past the cap, a length past the file's end, a payload that runs out, or a checksum that does not match"
    source: "`nexus/infrastructure/wal.py` 203-218"
  - claim: "A file as long as the marker whose marker reads wrong is read as holding nothing and refuses an append; a shorter one is read as holding nothing too, and an append writes it afresh over whatever it held"
    source: "`nexus/infrastructure/wal.py` 197-198 and 68-73, against the repair settled at 66 into 81-83"
---
# What a damaged record costs

A record that fails one of five checks costs everything after it: the read stops at that record and keeps the ones it had already taken. [A read that raises instead](when-a-read-raises-instead-of-stopping.md) ends differently.

## The five ways a record fails to hold up

A head too short to be a head. A length larger than the cap a single record may have. A length reaching past the end of the file. A payload that runs out before its length is reached. And a checksum that does not match the payload it is supposed to cover.

Any of the five ends the read at that point. The records already taken stand.

## A marker that reads wrong

A file long enough to carry the marker, whose marker reads wrong, is read as holding nothing at all, and it refuses [an append](how-a-record-reaches-the-log.md) too. The file yields nothing and takes nothing.

A file too short to carry a marker is read as holding nothing too. That one an append repairs, writing the file afresh over whatever it held.

## Related

- [When a read raises instead of stopping](when-a-read-raises-instead-of-stopping.md)
- [How a record reaches the log](how-a-record-reaches-the-log.md)
- [How the checkpoint rewrites the log](how-the-checkpoint-rewrites-the-log.md)

---

Created 2026-10-28 18:45 UTC · Last modified 2026-10-28 18:45 UTC
