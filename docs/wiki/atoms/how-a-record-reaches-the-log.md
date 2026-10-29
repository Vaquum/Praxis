---
row: N8-01
baseline: 49aa659
created: 2026-10-28 18:45 UTC
modified: 2026-10-28 18:45 UTC
evidence:
  - claim: "Each record is the payload behind a head of two figures, its length and a checksum of it"
    source: "`nexus/infrastructure/wal.py` 62-64 and 84-85"
  - claim: "A file missing or shorter than its marker is written afresh, the marker laid down before the record and the directory pushed to the disk after it"
    source: "`nexus/infrastructure/wal.py` 66 into 82-83 and 88-89"
  - claim: "A file past that is read for its marker, and an append into one whose marker reads wrong is refused before anything is written"
    source: "`nexus/infrastructure/wal.py` 68-73"
  - claim: "Where the marker reads right, the end of the last record whose head and checksum hold up is found, and only where the file runs past that end is it cut back to there and the cut pushed to the disk"
    source: "`nexus/infrastructure/wal.py` 74-80 under the test at 76, the end found at 94-116, its tests at 103-115"
  - claim: "Every record is pushed to the disk as it is appended, so one the caller was told was written is on the disk"
    source: "`nexus/infrastructure/wal.py` 86-87"
  - claim: "A host checks the marker and reads the log as it opens the store, numbering its own records on from the last record that read gives back"
    source: "`nexus/infrastructure/state_store.py` 114-116"
---
# How a record reaches the log

A record in the log is a payload with a head of two figures in front of it: how long the payload is, and a checksum of it.

## The two roads an append takes

A file that is missing, or too short to carry the marker opening the log, is written afresh. The marker goes down first, the record after it, and the directory holding the file is pushed to the disk once the record is in.

A file at least as long as the marker is read for its marker instead, and one whose marker reads wrong is refused before anything is written.

## The torn tail

Where the marker reads right, the append looks for the end of the last sound record. It walks the records from the front and stops at the first whose head will not do — too short, or naming a length past the cap or past the end of the file — or whose payload runs out or fails its checksum. Only where the file runs on past that end is it cut back to there, and the cut pushed to the disk.

A record whose checksum fails ends the search as surely as one that ran out mid-payload, so everything from it onward goes.

## What the writing is worth

Every record is pushed to the disk as it is appended, so a caller told its record was written can rely on it being on the disk.

## Where a record's number comes from

The head carries no number. A host checks the marker and reads the log as it opens its store, and numbers its own records on from the last record that read gives back.

## Related

- [What a damaged record costs](what-a-damaged-record-costs.md)
- [How the checkpoint rewrites the log](how-the-checkpoint-rewrites-the-log.md)

---

Created 2026-10-28 18:45 UTC · Last modified 2026-10-28 18:45 UTC
