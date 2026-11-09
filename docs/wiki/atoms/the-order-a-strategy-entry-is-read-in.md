---
row: N59-02
baseline: 49aa659
created: 2026-11-08 18:43 UTC
modified: 2026-11-08 18:43 UTC
evidence:
  - claim: "Each entry must be a mapping, and its name and its file are asked only to be there"
    source: "`nexus/infrastructure/manifest.py` 451-453, then 455-458, and 460-463"
  - claim: "Being text is asked of both by the record built at the end of the entry, which also refuses either padded"
    source: "`nexus/infrastructure/manifest.py` 549-556 into 136-142, and 144-146"
  - claim: "The signal must be a mapping, its series there and then text, its interval there and then a whole number with a true-or-false refused"
    source: "`nexus/infrastructure/manifest.py` 465-468, then 470-477, then 479-486"
  - claim: "A missing staleness answer becomes the one word accepted, so leaving it out and writing it are the same thing"
    source: "`nexus/infrastructure/manifest.py` 488, the one word insisted on at 68-70"
  - claim: "A timer's interval is asked its kind before its name is asked to be text"
    source: "`nexus/infrastructure/manifest.py` 520-522, then 524-526"
  - claim: "Timers left out become none at all, and a timer block that is not a list is refused before any entry in it is read"
    source: "`nexus/infrastructure/manifest.py` 499, and 501-503"
  - claim: "Two timers under one name are refused by the record rather than as they are read"
    source: "`nexus/infrastructure/manifest.py` 528-530, refused at 185-187"
---
# The order a strategy entry is read in

[A manifest](the-settings-a-host-is-given.md) lists its strategies, and each entry is read in a fixed order that decides which complaint a bad entry gets.

## Asked only to be there

The entry must be a mapping. Its name and the file it points at are then asked only to be present.

Being text is asked of neither until the record is built at the end of the entry, which refuses either of them padded or blank. The signal and the timers are read in between and have refusals of their own, so an entry naming a number where a name belongs can be turned back for its signal first, and is told about the name only where everything between passes.

## The signal

The signal must be a mapping. Its series is asked to be there and then to be text. Its interval is asked to be there and then to be a whole number, with a true-or-false refused for its kind although it counts as one.

Leaving the staleness answer out puts the single word that is accepted in its place, so writing that word and omitting it come to the same thing.

## The timers

Leaving the timers out leaves none. A timer block that is not a list is refused before any entry in it is read.

Inside an entry, the name is asked to be there, the interval asked to be there, the interval asked to be a whole number — and only then the name asked to be text. A timer naming a number and timed with a word is therefore refused for the word.

Two timers under one name pass the reading and are refused by the record.

## Related

- [The settings a host is given](the-settings-a-host-is-given.md)
- [The two refusals the manifest record adds](the-two-refusals-the-manifest-record-adds.md)
- [What a strategy's file must be](what-a-strategys-file-must-be.md)
