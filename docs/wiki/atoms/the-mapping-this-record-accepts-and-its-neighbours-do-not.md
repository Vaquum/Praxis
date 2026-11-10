---
row: N17-02
baseline: 49aa659
created: 2026-11-08 10:35 UTC
modified: 2026-11-08 10:35 UTC
evidence:
  - claim: "The per-strategy caps are refused unless what was handed in is a mapping of any kind"
    source: "`nexus/instance_config.py` 145-150"
  - claim: "A predictor's signal is refused unless what was handed in for its values is a dictionary, and a mapping that is not one is turned back"
    source: "`nexus/strategy/signal.py` 36-38"
  - claim: "A strategy's settings are refused on the same terms as the signal's values"
    source: "`nexus/strategy/params.py` 27-29"
---
# The mapping this record accepts and its neighbours do not

One record on this side asks for a mapping of any kind where two of its neighbours ask for a dictionary and turn back anything else.

## The two rules

The configuration's per-strategy caps are refused unless what was handed in is a mapping — any object that behaves as one will do.

[A predictor's signal](what-a-predictors-signal-is-checked-for.md) and [a strategy's settings](what-a-strategys-settings-ask-and-answer.md) are refused unless what was handed in is a dictionary. A mapping built on something else is turned back.

## What the difference lets through

A mapping that is not a dictionary reaches the configuration and is turned back by the other two. Running all three with such a mapping shows it: the configuration takes it and normalises it, and each of the other two refuses it by name.

So the same intent is written two ways on one side, and which objects a caller may hand over depends on which record it is handing them to.

## Related

- [What an instance's configuration refuses](what-an-instances-configuration-refuses.md)
- [What a predictor's signal is checked for](what-a-predictors-signal-is-checked-for.md)
- [What a strategy's settings ask and answer](what-a-strategys-settings-ask-and-answer.md)
