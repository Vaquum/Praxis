---
row: N37-02
baseline: 49aa659
created: 2026-11-08 16:46 UTC
modified: 2026-11-08 16:46 UTC
evidence:
  - claim: "The capital record refuses a key differing from its own trimmed form, by a test standing after the one that asks something is left"
    source: "`nexus/core/domain/capital_state.py` 78-83, after 72-77"
  - claim: "The record of what a strategy is declared as refuses a padded name the same way, in one test with the other two"
    source: "`nexus/infrastructure/manifest.py` 136-142"
  - claim: "The strategy base trims a name and keeps the trimmed form"
    source: "`nexus/strategy/base.py` 37 and 43"
  - claim: "The routing trims a name as it files a wrapper and as it looks one up"
    source: "`nexus/strategy/runner.py` 36 and 61"
  - claim: "A command's references are trimmed only to be tested, and are carried as they arrived"
    source: "`nexus/infrastructure/praxis_connector/trade_command.py` 101-103, which tests the trimmed form"
  - claim: "The shared check Praxis names its records by tests truth alone, so a name of blank space is kept"
    source: "`praxis/core/domain/_require_str.py` 28-30"
---
# The key this record will not trim for you

[The capital record](what-the-capital-record-refuses.md) refuses a strategy name with blank space around it, rather than trimming the space off and going on.

## Where the refusal comes

The key is trimmed once, and the trimmed form does two jobs: it is asked whether anything is left, and then it is compared with the key as it arrived. A key differing from its trimmed form fails that comparison.

[The record of what a strategy is declared as](what-settles-a-request-before-the-first-stage.md) does the same, in a single test that asks all three things of its name at once.

## The other three answers

[The base every strategy inherits from](the-name-a-strategy-answers-to.md) trims and keeps the trimmed form, so the padding is dropped and the name goes on.

[The routing](what-the-router-refuses.md) trims twice — once filing a wrapper under a name, once looking one up — so a padded name finds the wrapper filed without the padding.

[A command crossing the seam](what-a-command-is-checked-for.md) trims only to test that something is left, and carries the name as it arrived, padding and all. [The shared check Praxis names its records by](the-escape-in-the-shared-check-for-a-name.md) asks for truth alone, so a name of blank space alone is kept.

## What a reader should take from it

A padded name is refused by two records, shortened by two more, and kept as it stands by two. Which it meets first decides what happens to it.

## Related

- [What the capital record refuses](what-the-capital-record-refuses.md)
- [The name a strategy answers to](the-name-a-strategy-answers-to.md)
- [The escape in the shared check for a name](the-escape-in-the-shared-check-for-a-name.md)
