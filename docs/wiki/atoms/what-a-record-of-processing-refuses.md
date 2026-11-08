---
row: N18-01
baseline: 49aa659
created: 2026-11-09 23:00 UTC
modified: 2026-11-09 23:00 UTC
evidence:
  - claim: "The kind on a record of processing must be one of the named ones"
    source: "`nexus/infrastructure/praxis_connector/process_result.py` 37-39"
  - claim: "A record saying it failed must carry a reason"
    source: "`nexus/infrastructure/praxis_connector/process_result.py` 41-43"
  - claim: "A record saying it succeeded must carry none"
    source: "`nexus/infrastructure/praxis_connector/process_result.py` 45-47, reached rather than 43"
  - claim: "The kind is the one field whose type is asked; the flag the pair of checks turns on and the two saying what was changed are not asked for theirs"
    source: "`nexus/infrastructure/praxis_connector/process_result.py` 34-47, which asks a type once, at 37"
---
# What a record of processing refuses

The record saying how the processing of one report went is refused for failing any one of three checks.

## The kind

It must be one of the named ones. That is the one field of this record whose type is asked for.

## The pair that face each other

A record saying it failed must carry a reason. A record saying it succeeded must carry none.

Either way round is covered, so the record cannot say it failed and stay silent about why, nor say it succeeded and offer a reason anyway.

## The flag they turn on

Whether the record says it succeeded is never asked to be a flag. Nor are the two fields saying whether a position or the capital was changed.

So the pair of checks above reads whatever stands in that field for truth alone. Text put there is read the same way: a text with something in it sends the record down the success arm and an empty one down the failure arm, and each is then held to the reason rule of the arm it landed in.

## Related

- [What an entry in the log refuses](what-an-entry-in-the-log-refuses.md)
- [What stands where nothing was set](what-stands-where-nothing-was-set.md)
