---
row: P135-01
baseline: 49aa659
created: 2026-11-15 12:00 UTC
modified: 2026-11-15 12:00 UTC
evidence:
  - claim: "Every scheme start gathered from the history is walked, and one whose command has a terminal outcome is passed over"
    source: "`execution_manager.py` 1895, then 1896 into 1897"
  - claim: "The latest state it reached decides the next test, with an absent state read as running"
    source: "`execution_manager.py` 1899, then 1900"
  - claim: "A state that is anything but running passes it over"
    source: "`execution_manager.py` 1901 into 1902"
  - claim: "A mode that is not a scheme mode, a slice count below the minimum, or an interval at or below nought each pass it over"
    source: "`execution_manager.py` 1904-1908"
  - claim: "A volume-weighted scheme whose stored weights number fewer than that minimum is passed over and reported"
    source: "`execution_manager.py` 1911-1914 into 1920"
  - claim: "The venue's remembered rules give the lot step where any are held, and nothing where none are"
    source: "`execution_manager.py` 1922, then 1923"
  - claim: "A rebuild of the parameters or a replan of the slices that refuses passes it over and reports it as left for the boot cleanup"
    source: "`execution_manager.py` 1924-1933, then 1934 into 1940"
---
# What stops a scheme being resumed

A scheme start found in the history is resumed only if it survives five tests, and each of the five simply passes it over rather than ending the walk.

## The two about where it got to

A command with a terminal outcome is passed over. Then the latest state it reached is read, with an absent state taken as running — so a scheme that recorded a start and nothing else is treated as still going.

A state that is anything but running is passed over.

## The two about whether it can be rebuilt

A mode that is not a scheme mode, a slice count below the minimum, or an interval at or below nought each pass it over without a word.

A volume-weighted scheme whose stored weights number fewer than that minimum is passed over and reported, since the weights are the one thing its plan cannot be rebuilt without.

## The one about the plan

The parameters are rebuilt and the slices replanned, with the lot step taken from the venue's remembered rules where any are held and nothing where none are. A refusal from either passes the scheme over and reports it as left for the boot cleanup.

So a scheme whose plan can no longer be worked out is not resumed and not ended here either — it waits for the pass that ends orphaned commands.

## Related

- [What a restart puts back](what-a-restart-puts-back.md)
- [What one pass gathers for the schemes](what-one-pass-gathers-for-the-schemes.md)
- [What a resumed scheme comes back holding](what-a-resumed-scheme-comes-back-holding.md)
