---
row: N14-02
baseline: 49aa659
created: 2026-11-08 23:20 UTC
modified: 2026-11-08 23:20 UTC
evidence:
  - claim: "The outcome's reference on a strategy event must be text, and a text that has content but nothing left in it once trimmed is refused"
    source: "`nexus/infrastructure/strategy_event.py` 79-81, or else 83-89"
  - claim: "Empty text is allowed, the check for a blank one testing the text for content before it trims it"
    source: "`nexus/infrastructure/strategy_event.py` 83, which an empty text fails"
  - claim: "The field cannot be left as a none, and the record names empty text as its own default"
    source: "`nexus/infrastructure/strategy_event.py` 79-81, which refuses a none, with the default at 51"
---
# The empty reference a strategy event allows

One field of [a strategy event](what-a-strategy-event-is-checked-for.md) is allowed to be empty text while a blank one is refused.

## The two checks on it

It must be text: a none is turned back like anything else that is not text. Then a text that has content but nothing left in it once trimmed is turned back as well.

Empty text falls between the two. The second check asks whether the text has content before it trims it, and empty text fails that first half, so the trimming is never reached.

## Why the empty is let through

The field cannot be left as a none, and the record names empty text as the value it takes when nothing is given. So empty text is the only value the record has for saying the field was not filled in, and the second check is what lets it by.

## Related

- [What a strategy event is checked for](what-a-strategy-event-is-checked-for.md)
- [What the thirty-day cut leaves](what-the-thirty-day-cut-leaves.md)
