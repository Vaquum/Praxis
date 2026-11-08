---
row: N15-07
baseline: 49aa659
created: 2026-11-09 14:00 UTC
modified: 2026-11-09 14:00 UTC
evidence:
  - claim: "A hold is refused unless its flag is a true-or-false, its reason is text, and its moment, where one is given, a moment"
    source: "`nexus/core/domain/operational_mode.py` 44-46, or 48-50, or 52-54"
  - claim: "A hold standing active with no moment at all is let by, nothing weighing the two against each other"
    source: "`nexus/core/domain/operational_mode.py` 52, which lets a none by, against 44-46"
  - claim: "A mode state is refused unless its mode is one of the named ones, its driver text with something left in it once trimmed, and its moment a moment"
    source: "`nexus/core/domain/operational_mode.py` 143-145, or 147-149, or 151-153"
  - claim: "A strategy's mode state is refused unless its reference is text with something left in it once trimmed and what it holds is a mode state"
    source: "`nexus/core/domain/operational_mode.py` 171-173, or 175-177"
  - claim: "Two holds force entries blocked, and the record gathering them answers whether either is standing"
    source: "`nexus/core/domain/operational_mode.py` 113-114 into 119"
  - claim: "Neither record gathering holds makes a check of its own"
    source: "`nexus/core/domain/operational_mode.py` 77-82, or 113-114, neither followed by a check"
---
# What the records of the mode refuse

Five records hold the mode and the reasons for it. Three check themselves and two check nothing.

## A single hold

Refused unless its flag is a true-or-false, its reason is text, and its moment, where one is given, a moment.

An empty reason is let by: the check asks for text and not for content. So is a hold standing active with no moment at all — nothing weighs the flag against the moment, and a hold that says it is holding need not say since when.

## The mode itself

A mode state is refused unless its mode is one of the named ones, its driver is text with something left once the blank space is trimmed off, and its moment is a moment. [What that moment is not asked for](the-moments-with-no-marker.md) is its own subject.

A strategy's mode state is refused unless its reference is text with something left once trimmed, and unless what it holds is a mode state.

## The two gatherings

Six holds force a halt, and two force entries blocked. Each set is gathered in a record that makes no check of its own and answers one question: whether any of the holds it carries is standing.

So a gathering takes whatever holds it is handed, and which of them outranks which is settled elsewhere.

## Related

- [The moments with no marker](the-moments-with-no-marker.md)
- [What a stopping host halts first](what-a-stopping-host-halts-first.md)
- [How the mode is settled](how-the-mode-is-settled.md)
