---
row: N73-04
baseline: 49aa659
created: 2026-11-13 04:30 UTC
modified: 2026-11-13 05:00 UTC
evidence:
  - claim: "A decision that was allowed gives nothing at all"
    source: "`nexus/core/validator/price_stage.py` 217-218"
  - claim: "A decision refused at some other stage gives nothing either, so this reads only its own stage's refusals"
    source: "`nexus/core/validator/price_stage.py` 220-221"
  - claim: "Three reasons give an answer marking both the strategy's owner and the platform's operators, at the gravest level"
    source: "`nexus/core/validator/price_stage.py` 224-233"
  - claim: "Those three are a reading of the market that could not be had, one that was unusable, and a book too old"
    source: "`nexus/core/validator/price_stage.py` 225, and 226, and 227"
  - claim: "The first of the three is also given for a configured source that is absent, and for a request carrying no reference price where a cap applies"
    source: "`nexus/core/validator/price_stage.py` 317-326, and 327-336"
  - claim: "Two reasons give an answer marking the strategy's owner alone, at the mildest level"
    source: "`nexus/core/validator/price_stage.py` 235-240"
  - claim: "Those two are a spread above its cap and a deviation above its cap"
    source: "`nexus/core/validator/price_stage.py` 235, raised at 301-310 and 361-370"
  - claim: "Every other reason gives a middle answer marking both, so a reason added later is sorted without this step being changed"
    source: "`nexus/core/validator/price_stage.py` 242-246, reached past 224 and 235"
  - claim: "All three answers mark the strategy's owner, and the answer is a record of flags and a level rather than a message sent"
    source: "`nexus/core/validator/price_stage.py` 230, or 237, or 243, into 182-188"
---
# Who is told about a price refusal

A price refusal is turned into a routing answer by one step, which sorts the reasons into three groups.

## What it reads

Only its own stage's refusals. A decision that was allowed gives nothing, and so does one refused at some other stage.

## The gravest group

Three reasons: a reading of the market that could not be had, one that was unusable, and a book too old. Each gives an answer marking both the strategy's owner and the platform's operators, at the gravest level.

The first of those three is given for more than it sounds like. The same reason is raised where the configured source for a reference price is absent, and where a request carries no reference price although a cap applies to it — so it covers a configuration and a request as well as missing data.

## The mildest group

Two reasons: a spread above its cap, and a deviation above its cap. Each marks the strategy's owner alone, at the mildest level.

## Everything else

A middle answer, marking both.

So a reason added to the stage later is sorted without this step being changed — into that middle group, until somebody puts it in one of the two named ones.

## What the answer is

A record of two flags and a level. All three answers mark the strategy's owner, and what is done with a marked answer is settled by whoever asked for it.

## Related

- [What the price check weighs](what-the-price-check-weighs.md)
- [What the price records refuse](what-the-price-records-refuse.md)
