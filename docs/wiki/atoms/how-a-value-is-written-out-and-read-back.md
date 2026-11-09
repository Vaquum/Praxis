---
row: P93-01
baseline: 49aa659
created: 2026-11-14 00:00 UTC
modified: 2026-11-14 00:00 UTC
evidence:
  - claim: "A figure the writer cannot write natively is written as text where it is a decimal figure"
    source: "`event_spine.py` 318 into 319"
  - claim: "Anything else the writer cannot write raises, naming the kind that arrived"
    source: "`event_spine.py` 320-321"
  - claim: "Reading back, nothing stays nothing whatever it was meant to become"
    source: "`event_spine.py` 337 into 338"
  - claim: "A decimal figure is rebuilt through its text, so what was written is what is parsed"
    source: "`event_spine.py` 352 into 353"
  - claim: "A moment is parsed from text, and a named value is rebuilt by calling its own kind"
    source: "`event_spine.py` 354 into 355, or 356 into 357"
  - claim: "A value whose kind matches none of those is handed back exactly as it arrived"
    source: "`event_spine.py` 351, standing as the answer at 365"
---
# How a value is written out and read back

The spine writes events as JSON and reads them back into the kinds they came from, and each direction has one rule for figures.

## Going out

A figure the writer cannot write natively is written as text where it is a decimal figure. Anything else it cannot write raises, naming the kind that arrived — so an event carrying something unexpected fails at the write rather than being written in some other shape.

## Coming back

Nothing stays nothing, whatever it was meant to become. A decimal figure is rebuilt through its text, so what was written is what is parsed, and no precision is lost between the two.

A moment is parsed from text. A named value is rebuilt by calling its own kind with what was stored.

## The road that changes nothing

A value whose kind matches none of those is handed back exactly as it arrived. The result starts as the value itself and is replaced only where a rule applies.

So a kind the reading has no rule for passes through untouched, and whether that is right depends on what JSON happened to make of it — a whole number stays a whole number, and a figure with a fraction comes back as a floating one.

## Related

- [The three shapes a coercion looks inside](the-three-shapes-a-coercion-looks-inside.md)
