---
row: P26-02
baseline: 49aa659
created: 2026-11-08 16:02 UTC
modified: 2026-11-08 16:02 UTC
evidence:
  - claim: "A refusal with no reason of its own, or an empty one, is given the word for being refused"
    source: "`outcome_translator.py` 329 into 336"
  - claim: "A reason of blank space alone is truthy, so it is kept and passed on as it stands"
    source: "`outcome_translator.py` 329, which tests the reason's truth"
  - claim: "The record on the far side refuses a refusal whose reason is blank space, so building it raises"
    source: "`nexus/infrastructure/praxis_connector/trade_outcome.py` 119-122, reached from `outcome_translator.py` 331-337"
  - claim: "An ending that is an expiry carries no reason at all"
    source: "`outcome_translator.py` 341-343"
  - claim: "Any other ending carries its own reason where it has one, and none where it has not"
    source: "`outcome_translator.py` 344-346"
---
# The words an ending carries

An outcome crossing to Nexus as a refusal or an ending may carry words saying why, and where those words come from differs by the kind.

## A refusal

The reason Praxis recorded, or the single word for being refused where Praxis recorded nothing or an empty reason. [The record on the far side insists on words](the-reason-an-outcome-may-carry.md), and this is what guarantees them.

## The reason of blank space

Between those two cases sits a third. A reason of blank space alone counts as something to the test here, so it is kept and passed on as it stands — and the record on the far side asks for something left once the blank space is trimmed, and refuses it.

So translating such an outcome raises rather than crossing. [Praxis keeps a name of blank space](the-escape-in-the-shared-check-for-a-name.md) in several of its own records; this is where that leniency meets a record that will not have it.

## An ending

An expiry crosses with no reason at all, whatever Praxis recorded — the kind says it expired, and nothing is added.

Any other ending crosses as [a cancellation](how-a-trade-is-cancelled.md), carrying the reason Praxis recorded where there is one and nothing where there is not.

## Related

- [How an outcome crosses back](how-an-outcome-crosses-back.md)
- [The reason an outcome may carry](the-reason-an-outcome-may-carry.md)
- [What the translator remembers](what-the-translator-remembers.md)
