---
row: P26-01
baseline: 49aa659
created: 2026-11-11 09:00 UTC
modified: 2026-11-11 09:30 UTC
evidence:
  - claim: "The cap on remembered finished commands must be a whole number above nought"
    source: "`outcome_translator.py` 126-128"
  - claim: "A true-or-false of true passes that test and is kept, bounding the filing at one"
    source: "`outcome_translator.py` 126 admitting it, kept at 133 and read at 259-260"
  - claim: "Marking a command finished sets its flag, files its name and moves that name to the end"
    source: "`outcome_translator.py` 256-258"
  - claim: "Names past the cap are dropped oldest first"
    source: "`outcome_translator.py` 259-260"
  - claim: "The command's own record is forgotten as its name is filed"
    source: "`outcome_translator.py` 261"
  - claim: "An outcome arriving for a command whose name has been dropped is given a fresh record"
    source: "`outcome_translator.py` 156 finding no name, then 166"
---
# What the translator remembers

[The translator](how-an-outcome-crosses-back.md) keeps two things: a record per command still running, and the names of commands that have finished. The second is capped.

## The cap

A whole number above nought. The cap is what bounds how far back [a late outcome can be recognised as late](outcomes-that-never-come-back.md).

A true-or-false passes that test — true is a whole number here, and nothing stands in the way as it does in the records that test for one first. A cap of true is kept as it arrived and read as one, so the filing holds at most one name.

## What finishing a command does

Its record is flagged finished. Its name is filed among the finished and moved to the end of that filing, so the filing runs oldest first.

Names past the cap are then dropped from the old end, one at a time, until the filing fits.

The command's own record goes at the same moment.

## What a dropped name costs

An outcome for a command whose name is still filed is dropped, and nothing crosses.

An outcome for a command whose name has been dropped for age is treated as the first anyone has heard of it: a fresh record is made and the outcome is translated on its own terms. So the cap is the length of the translator's memory, and past it a finished command can start again.

## Related

- [How an outcome crosses back](how-an-outcome-crosses-back.md)
- [Outcomes that never come back](outcomes-that-never-come-back.md)
- [The words an ending carries](the-words-an-ending-carries.md)
