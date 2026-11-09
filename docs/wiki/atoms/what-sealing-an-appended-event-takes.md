---
row: P97-02
baseline: 49aa659
created: 2026-11-14 02:00 UTC
modified: 2026-11-14 02:00 UTC
evidence:
  - claim: "An event of a kind the registry does not hold cannot be appended at all"
    source: "`event_spine.py` 1160-1161"
  - claim: "Its moment becomes text and its whole self becomes bytes before any row is written"
    source: "`event_spine.py` 1162, then 1163"
  - claim: "The seal it will hang from is read before the row exists"
    source: "`event_spine.py` 1164, ahead of 1165"
  - claim: "The row is written first and its own number taken from the writing, with a missing number raising"
    source: "`event_spine.py` 1165-1166 into 1168-1170, then 1171"
  - claim: "The seal is then worked out from that number together with the moment, the kind and the bytes"
    source: "`event_spine.py` 1172-1174"
  - claim: "A second write puts the seal and the one before it onto the row just written"
    source: "`event_spine.py` 1175-1176, the number answered at 1178"
  - claim: "The seal to hang from is the highest row's own"
    source: "`event_spine.py` 1199"
  - claim: "Both an empty file and a tip with no seal answer the anchor instead"
    source: "`event_spine.py` 1193-1194, then 1196 into 1197"
---
# What sealing an appended event takes

Sealing an event takes two writes: one to make the row and learn its number, and one to put the seal on it.

## Before either write

An event of a kind the registry does not hold cannot be appended at all. Its moment becomes text and its whole self becomes bytes, and the seal it will hang from is read — all before any row exists.

## The first write

The row is written, and its own number is taken from the writing. A writing that hands back no number raises, so sealing requires a number the writing actually gave.

## The seal

Worked out from that number together with the moment, the kind and the bytes. So the number is part of what is sealed, which is why it has to be learned before the seal can be made, and why the seal cannot be written in the same breath as the row.

## The second write

It puts the seal and the one before it onto the row just written. The row therefore exists unsealed for the moment between the two writes, inside the one transaction.

## What a seal hangs from

The highest row's own. Both an empty file and a tip carrying no seal answer the anchor instead — so a file that still ends in unsealed rows starts its chain afresh from the anchor rather than from the last row.

## Related

- [What an append does in one transaction](what-an-append-does-in-one-transaction.md)
