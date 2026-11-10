---
row: P152-01
baseline: 49aa659
created: 2026-11-09 11:51 UTC
modified: 2026-11-09 11:51 UTC
evidence:
  - claim: "An order the account's own state holds nothing for is reported and the re-confirming abandoned"
    source: "`execution_manager.py` 7233-7234, then 7236 into 7243"
  - claim: "Otherwise a submission is built naming the list the venue confirmed and every leg of it"
    source: "`execution_manager.py` 7245-7253"
  - claim: "The exit command is pointed at that list before the submission is written down"
    source: "`execution_manager.py` 7254, ahead of 7255"
  - claim: "The submission is then written to the record and applied"
    source: "`execution_manager.py` 7255, then 7256"
  - claim: "A record that the protection is active is written next, naming the version the bracket already held and that list"
    source: "`execution_manager.py` 7258-7264, then 7265"
  - claim: "Only then is the bracket pointed at the list, called active, and cleared of both the moment it became doubtful and the replacement it was owing"
    source: "`execution_manager.py` 7266, then 7267, then 7268, then 7269"
---
# How a protection in doubt is re-confirmed

A protection whose fate was in doubt is re-confirmed by writing it back as active, using whichever list the venue said is working.

## The one thing that stops it

An order the account's own state holds nothing for. The re-confirming is reported and abandoned, and the bracket stays in doubt for the next pass.

A submission written for an order absent from the state would be applied to nothing, leaving the legs' fills with nowhere to route. So the absence is taken as a reason to wait rather than a reason to write.

## The order of the writing

The exit command is pointed at the confirmed list first — before the submission is written down. Then the submission, naming that list and every leg of it, written to the record and applied.

Then a record that the protection is active, naming the version the bracket already held and that same list.

Only after all of that is the bracket itself pointed at the list, called active, and cleared of both the moment it became doubtful and the replacement it was owing.

## What the version says

The version is the one the bracket already held, so re-confirming does not advance it. The list that turned out to be working is recorded under the version it belonged to, whichever of the two candidates it was.

## Related

- [What a protection of unknown fate is rebuilt as](what-a-protection-of-unknown-fate-is-rebuilt-as.md)
- [When a bracket's protection becomes active](when-a-brackets-protection-becomes-active.md)
- [What the venue is asked when no protection is working](what-the-venue-is-asked-when-no-protection-is-working.md)
