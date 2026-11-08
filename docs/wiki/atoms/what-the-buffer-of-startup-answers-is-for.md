---
row: N72-02
baseline: 49aa659
created: 2026-11-13 03:30 UTC
modified: 2026-11-13 04:00 UTC
evidence:
  - claim: "An answer is buffered rather than submitted where no road for submitting was given when the sequencer was built"
    source: "`nexus/startup/sequencer.py` 740, the road read at 747"
  - claim: "Draining answers at once where the buffer holds nothing"
    source: "`nexus/startup/sequencer.py` 210-211"
  - claim: "The buffer is taken into a local name and the field emptied before anything is submitted"
    source: "`nexus/startup/sequencer.py` 213, then 214"
  - claim: "So a second draining finds nothing, unless a further asking of the strategies has filled the field again"
    source: "`nexus/startup/sequencer.py` 214, read by 210, written again at 741-744"
  - claim: "Each strategy's answers are submitted in the order the buffer holds them, and a strategy whose list is empty is passed over"
    source: "`nexus/startup/sequencer.py` 216, then 217-218"
  - claim: "An ordinary failure of the submitting is logged against that strategy and the next strategy's answers are still submitted"
    source: "`nexus/startup/sequencer.py` 219-225"
  - claim: "Because the field was emptied first, the sequencer holds those answers nowhere afterwards and submits them nowhere again"
    source: "`nexus/startup/sequencer.py` 214 standing before 220, with no second attempt in 216-225"
---
# What the buffer of startup answers is for

[A strategy's answer at startup](what-a-strategys-startup-answer-does.md) is buffered where no road for submitting it was given when the sequencer was built, and something must come back for it.

## What draining does

It answers at once where the buffer holds nothing.

Otherwise it takes the buffer into a local name and empties the field — before anything is submitted. So a second draining finds nothing, unless a further asking of the strategies has filled the field again.

Each strategy's answers are then submitted in the order the buffer holds them, and a strategy whose list is empty is passed over.

## A failure of the submitting

An ordinary failure is logged against that strategy, and the next strategy's answers are still submitted.

## What a failure costs here

The field was emptied before the submitting began, and nothing in the draining tries twice.

So after a failed submitting the sequencer holds those answers nowhere and will not submit them again. What the road for submitting did with them before it failed is that road's business, and this module records nothing of it.

## Related

- [What a strategy's startup answer does](what-a-strategys-startup-answer-does.md)
- [Starting a host](starting-a-host.md)
